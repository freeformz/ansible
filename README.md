# Ansible Bits

Install via: `ansible-galaxy collection install freeformz.ansible`

## Tailscale Inventory Plugin

Requires a tailscale api key.

Creates groups for each tag (when `tag_groups = true` - Defaults to true), each os (when `os_groups = true` - Defaults to true), 
and online/offline status (when include_online_offline_groups == true - Defaults to true).

Tags in Tailscale start with `tag:`. This prefix is stripped when `strip_tag` == true (the default), otherwise it is converted to `tag_`.

See `ansible-doc -t inventory freeformz.ansible.tailscale` for more documentation and all the options.

Run `ansible-inventory --list` to see the output. If you are playing with options, you can use this command to see how they affect the inventory.

Data from the [Tailscale Tailnet Get Devices API](https://github.com/tailscale/tailscale/blob/main/api.md#tailnet-devices-get) is converted
from camelCase to snake_case and provided in the inventory.

### Example

This is a watered down version of the config of my personal home lab tailscale + ansible setup.

`ansible.cfg`

```ini
[inventory]
enable_plugins = freeformz.ansible.tailscale

[defaults]
inventory = ./inventory/tailscale.yaml
```

`./inventory/tailscale.yaml`

```yaml
plugin: freeformz.ansible.tailscale # must be freeformz.ansible.tailscale
ansible_host: ipv4                  # ipv4, ipv6, dns, or host_name - Depends on how you referred to the hosts before this
api_key: "<a tailscale api key>"    # static Tailscale API Key or Jinja2 template - https://tailscale.com/kb/1101/api/
tailnet: freeformz.github           # The name of your tailnet - What you see at the top left of https://login.tailscale.com/admin/machines
```

`ansible-inventory --list`

```json
{
    "_meta": {
        "hostvars": {
            "edwards-boxen": {
                "addresses": [
                    "1.2.3.4",
                    "aaaa:bbbb:cccc:dddd:eeee:ffff:gggg:hhhh"
                ],
                "advertised_routes": [],
                "ansible_host": "1.2.3.4",
                "authorized": true,
                "blocks_incoming_connections": false,
                "client_connectivity": {
                    "client_supports": {
                        "hair_pinning": false,
                        "ipv6": true,
                        "pcp": true,
                        "pmp": true,
                        "udp": true,
                        "upnp": true
                    },
                    "derp": "",
                    "endpoints": [
                        "<redacted>"
                    ],
                    "latency": {
                        "_dallas": {
                            "latency_ms": 197.155708
                        },
                        "_san _francisco": {
                            "latency_ms": 99.882166,
                            "preferred": true
                        },
                        "_seattle": {
                            "latency_ms": 99.97449999999999
                        }
                    },
                    "mapping_varies_by_dest_ip": true
                },
                "client_version": "1.28.0-t80313cdee-gd26dd4a68",
                "created": "2021-08-06T21:32:18Z",
                "enabled_routes": [],
                "expires": "2023-01-28T21:47:09Z",
                "ipv4": "1.2.3.4",
                "ipv6": "aaaa:bbbb:cccc:dddd:eeee:ffff:gggg:hhhh",
                "is_external": false,
                "key_expiry_disabled": false,
                "last_seen": "2022-08-10T03:38:41Z",
                "machine_key": "mkey:<redacted>",
                "name": "edwards-iphone.freeformz.github",
                "node_key": "nodekey:<redacted>",
                "os": "iOS",
                "status": "online",
                "update_available": false,
                "user": "freeformz@github",
                "tags": [
                    "..."
                ]
            },
        },
    },
    "all": {
        "children": [
            "ios",
            "linux",
            "offline",
            "online",
            "ungrouped"
            "atag",
        ]
    },
    "atag": {
        "hosts": [
            "a",
            "b",
            "c"
        ]
    },
    "ios": {
        "hosts": [
            "edwards-boxen"
        ]
    },
    "linux": {
        "hosts": [
            "..."
        ]
    },
    "offline": {
        "hosts": [
            "..."
        ]
    },
    "online": {
        "hosts": [
            "edwards-boxen",
            "..."
        ]
    },
    "ungrouped": {
        "hosts": [
            "..."
        ]
    },
}
```

### OAuth example

If you want to use [OAuth](https://tailscale.com/kb/1215/oauth-clients) to authenticate to the Tailscale API,
especially useful as static API tokens will expire after some time, then you can use an external script to
fill in the token:

`./inventory/tailscale.yaml`

```yaml
plugin: freeformz.ansible.tailscale # must be freeformz.ansible.tailscale
ansible_host: ipv4                  # ipv4, ipv6, dns, or host_name - Depends on how you referred to the hosts before this
api_key: "{{ lookup('ansible.builtin.pipe', './scripts/get-tailscale-api-token' }}"
tailnet: freeformz.github           # The name of your tailnet - What you see at the top left of https://login.tailscale.com/admin/machines
```

`./scripts/get-tailscale-api-token`

```bash
#!/bin/bash
set -euo pipefail

# Ensure -x is disabled so secrets aren't accidentally printed
set +x

TAILSCALE_API_RESPONSE=$(curl --retry 5 --retry-max-time 120 --silent \
                         -d "client_id=${TAILSCALE_CLIENT_ID}" \
                         -d "client_secret=${TAILSCALE_CLIENT_SECRET}" \
                         "https://api.tailscale.com/api/v2/oauth/token")

TAILSCALE_API_TOKEN=$(echo "${TAILSCALE_API_RESPONSE}" | jq -r '.access_token')

if [[ "${TAILSCALE_API_TOKEN}" == 'null' ]]
then
    >&2 echo 'ERROR: Tailscale API returned an invalid API token, aborting!'
    >&2 echo
    >&2 echo "${TAILSCALE_API_RESPONSE}"
    exit 1
fi

echo "${TAILSCALE_API_TOKEN}"
```

## Contributors

* [Simon Baerlocher](https://github.com/sbaerlocher)
* [Wes Mason](https://github.com/1stvamp)
