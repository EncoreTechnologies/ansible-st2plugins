# (c) 2018, Nick Maludy <nmaludy@gmail.com>
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: st2kv
    version_added: N/A
    short_description: Grab values from the StackStorm (st2) key/value datastore
    description:
      - lookup metadata for a playbook from the key value store in StackStorm (st2).
    requirements:
      - 'python-requests (python library http://docs.python-requests.org/en/master/user/install/)'
    options:
      _terms:
        description: key(s) to retrieve
        type: list
        required: True
      api_url:
        type: string
        description: URL of the API endpoint on the StackStorm server.
        default: https://localhost/api
        required: False
      hostname:
        type: string
        description:
          - If api_url isn't specified then this will be the hostname used
            to create the URL string: https://<hostname>/api
        default: localhost
        required: False
      port:
        type: string
        description:
          - If api_url isn't specified then this will be the port used
            to create the URL string: https://<hostname>:<port>/api
          - If no port is specified (default) then the :<port> will not be used
            when creating the URL string.
        default: None
        required: False
      ssl_verify:
        type: boolean
        description: Should verification be performed for the SSL certificate?
        default: true
      auth_token:
        type: string
        description: Authentication token received from StackStorm auth.
        env:
          - name: ST2_ACTION_AUTH_TOKEN
          - name: ST2_AUTH_TOKEN
      api_key:
        type: string
        description:
           - API key generated in StackStorm. Can be created using the
             command: 'st2 apikey create'
        env:
          - name: ST2_API_KEY
      decrypt:
        type: boolean
        description:
          - Should the value be decrypted by StackStorm. This should be set to
            True if you would like to read encrypted keys.
        default: False
      user:
        type: string
        description:
          - Username of the StackStorm user that owns the key.
          - Needed when reading user-scoped keys
"""

EXAMPLES = """
  - debug: msg='key contains {{item}}'
    with_st2kv:
      - 'system.key_to_retrieve'

  - name: retrieving a KV when ansible is called from a StackStorm action
    debug:
      msg: "{{ lookup('st2kv', 'system.some_key') }}"

  - name: retrieving a KV from a remote host using an API key
    debug:
      msg: "{{ lookup('st2kv', 'system.my_key', hostname='stackstorm.domain.tld', api_key="xyz123") }}"

  - name: retrieving a KV from a remote host using an Auth token
    debug:
      msg: "{{ lookup('st2kv', 'system.my_key', hostname='stackstorm.domain.tld', auth_token="ysfd456") }}"

  - name: retrieving a KV in user scope
    debug:
      msg: "{{ lookup('st2kv', 'user.my_key', user='dave', hostname='stackstorm.domain.tld', api_key="xyz123") }}"

  - name: retrieving a KV using a custom API url
    debug:
      msg: "{{ lookup('st2kv', 'system.different_key', api_url='http://st2.domain.tld/st2/api, api_key="xyz123") }}"
"""

RETURN = """
  _term:
    description:
      - value(s) stored in the StackStorm (st2) datastore
"""

import os
import sys
from ansible.module_utils.six.moves.urllib.parse import urlparse
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

try:
    import requests
    HAS_REQUESTS = True
except ImportError as e:
    HAS_REQUESTS = False


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        if not HAS_REQUESTS:
            raise AnsibleError('"requests" module is required for st2kv lookup. see http://docs.python-requests.org/en/master/user/install/')

        values = []
        try:
            for term in terms:
                api_url = kwargs.get('api_url', None)
                if not api_url:
                    hostname = kwargs.get('hostname', 'localhost')
                    port = kwargs.get('port', None)
                    if port:
                        api_url = 'https://{}:{}/api'.format(hostname, port)
                    else:
                        api_url = 'https://{}/api'.format(hostname)

                ssl_verify = kwargs.get('ssl_verify', True)
                if not ssl_verify:
                    requests.packages.urllib3.disable_warnings()

                # Priority:
                #  1. auth_token : argument to the function
                #  2. ST2_ACTION_AUTH_TOKEN : environment variable
                #  3. ST2_AUTH_TOKEN : environment variable
                auth_token = kwargs.get('auth_token', None)
                if not auth_token:
                    auth_token = os.environ.get('ST2_ACTION_AUTH_TOKEN')
                if not auth_token:
                    auth_token = os.environ.get('ST2_AUTH_TOKEN')

                # Priority:
                #  1. api_key : argument to the function
                #  2. ST2_API_KEY : environment variable
                api_key = kwargs.get('api_key', None)
                if not api_key:
                    api_key = os.environ.get('ST2_API_KEY')

                decrypt = kwargs.get('decrypt', False)
                user = kwargs.get('user', None)

                headers = {}
                if auth_token:
                    headers['X-Auth-Token'] = auth_token
                elif api_key:
                    headers['St2-Api-Key'] = api_key
                else:
                    raise AnsibleError(
                        "Error no auth information provided. You must specify"
                        " either auth_token or api_key parameters. Or, set one"
                        " of the following environment variables: ST2_AUTH_TOKEN,"
                        " ST2_ACTION_AUTH_TOKEN, or ST2_API_KEY")

                # parse the term into scope and key
                scope, key = self.parse_scope_key(term)

                # build the URL based on scope and key names
                url = '{}/v1/keys/{}?scope={}'.format(api_url, key, scope)
                # append the global options to the URL
                if decrypt:
                    url += "&decrypt=true"
                if user:
                    url += "&user={}".format(user)

                # make the query
                response = requests.get(url, headers=headers, verify=ssl_verify)
                response.raise_for_status()
                data = response.json()

                # append to results
                values.append(data["value"])
        except Exception as e:
            raise AnsibleError(
                "Error locating '%s' in kv store. Error was %s" % (term, e))

        return values

    def parse_scope_key(self, term):
        """Parses a term string into a scope and key.
        The valid formats for the string is:
          key        ('system' scope assumed)
          scope.key

        The parts of the string are delimited by '.'.
        If a string is given with no '.' then the given string will be the key
        and the 'system' scope will be used as the default.
        If the first part of the string is NOT "st2kv" the the first part will
        be used as the scope and the remaining parts will be joined back together
        with '.' and used as the key.
        If the first part of the string is "st2kv" then this part will be removed
        and the rest of the string will be parsed like a 2-part string (above).

        Examples:
          term: my_really_sweet_key
            scope: system
            key: my_really_sweet_key

          term: system.my.coolkey
            scope: system
            key: my.coolkey
        """
        # is the term None or empty string?
        if not term:
            raise AnsibleError("Error - The key can't be an empty string or null")

        # break apart the term into parts using '.' as the delimiter
        parts = term.split('.')
        if len(parts) == 1:
            # the term doesn't contain a '.' meaning there is only one part
            # then return this single part as the key in the default "system"
            # scope
            return ("system", parts[0])
        elif len(parts) < 2:
            # does the term contain the required 2 parts (scope and key)?
            raise AnsibleError("Error - The key doesn't contain a scope and a"
                               " key delimited by a '.' (example: system.key)."
                               " Error in key: {}".format(term))

        # the scope is the text before the first '.'
        scope = parts[0]
        # the key is the text after the first '.'
        key = '.'.join(parts[1:])
        return (scope, key)
