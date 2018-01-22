# ansible-st2plugins

Plugins for ansible that communicate with the StackStorm (st2) API.

## Installation

### Pre-requisites 

This plugin uses the `requests` python package (found [here](http://docs.python-requests.org/en/master/user/install/)).
You'll need to install that package so that it's available to ansible during runtime.

``` shell
pip install requests
```

### Option 1 - Standard Directories

Copy the `lookup_plugins` directory into one of the following default directories
secified here: https://docs.ansible.com/ansible/devel/config.html#default-lookup-plugin-path

Default Directories:
```shell
~/.ansible/plugins/lookup_plugins/
/usr/share/ansible_plugins/lookup_plugins
```

### Option 2 - Playbook Directory

According to the [lookup_plugin documentation](https://docs.ansible.com/ansible/devel/plugins/lookup.html#enabling-lookup-plugins)
you can also copy the `lookup_plugins` directory into the same directory as your
playbook:

```shell
cp -r lookup_plugins/ /path/to/directory/where/your/playbook/lives/
```

### Option 3 - Ansible Config

Edit your ansible config `ansible.cfg` and add in the path to this repositories 
`lookup_plugins` directory into the `[defaults]` section:

``` ini
[defaults]
lookup_plugins = ~/.ansible/plugins/lookup_plugins/:/usr/share/ansible_plugins/lookup_plugins:~/git/ansible-st2plugins/lookup_plugins
```

## Usage

### Lookup Plugins

The `st2kv` plugin reads data from the StackStorm (st2) key/value datastore
from within ansible. 

``` yaml
  - name: retrieving a KV from StackSTorm
    debug:
      msg: "{{ lookup('st2kv', 'system.my_key') }}"
```

In order for this to work ansible will need to authenticate with StackStorm.
Authentication can be accomplished in several ways:

 * API key from within ansible
 * API key from an environment variable
    * `ST2_API_KEY `
 * Auth token from within ansible
 * Auth token from an environment variable(s)
    * `ST2_ACTION_AUTH_TOKEN`
    * `ST2_AUTH_TOKEN`

#### API Key Auth

In this first example we're retrieving the key `system.my_key` from a remote
StackStorm host using an API key generated from command `st2 apikey create`.
For more info on creating API keys see the StackStorm documentation [here](https://docs.stackstorm.com/authentication.html#api-keys).
Once the API key is obtained you can simply pass it in to the `lookup` function
using the parameter `api_key`:

``` yaml
  - name: retrieving a KV from a remote host using an API key
    debug:
      msg: "{{ lookup('st2kv', 'system.my_key', hostname='stackstorm.domain.tld', api_key="xyz123") }}"
```

Sometimes it's conveient to utilize environment variables to store information, 
for example when invoking multiple consecutive playbooks. In this case the plugin
allows the API key to be read from an environment variable `ST2_API_KEY`. When
using an environment variable, make sure to NOT specify the `api_key` parameter
in the lookup function:


``` yaml
  - name: retrieving a KV from a remote host using an API key (assumes ST2_API_KEY 
        environment variable is set)
    debug:
      msg: "{{ lookup('st2kv', 'system.my_key', hostname='stackstorm.domain.tld') }}"
```

#### Auth Token

Auth tokens work the same as API keys except different names are used.
For an auth token passed directly into the lookup function use the `auth_token` 
paramter:

``` yaml
  - name: retrieving a KV from a remote host using an Auth token
    debug:
      msg: "{{ lookup('st2kv', 'system.my_key', hostname='stackstorm.domain.tld', auth_token="ysfd456") }}"
```

For utilizing environment variables you can either set `ST2_AUTH_TOKEN` or 
`ST2_ACTION_AUTH_TOKEN`. 

#### Calling from a StackStorm action

We've tried to make the ansible integration as easy as possible. If you
invoke ansible from a StackStorm action using something like the 
[`stackstorm-ansible`](https://github.com/StackStorm-Exchange/stackstorm-ansible)
or the [`local-shell-cmd` runner](https://docs.stackstorm.com/reference/runners.html#local-command-runner-local-shell-cmd)
then the authentication is handled for you automatically! This happens
because when StackStorm invokes an action it sets the environment
variable `ST2_ACTION_AUTH_TOKEN` with the auth token of the current action
being run. This means, when calling directly from StackStorm, can your
lookup can be as simple as:

``` yaml
  - name: retrieving a KV from StackSTorm (when called from StackStorm)
    debug:
      msg: "{{ lookup('st2kv', 'system.my_key') }}"
```

#### Reference

A complete reference documentation for the `st2kv` lookup plugin:

```yaml
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
```
