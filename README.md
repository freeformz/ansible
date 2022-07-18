# Ansible Bits

Install via: `ansible-galaxy collection install freeformz.ansible`

## Tailscale Inventory Plugin

`ansible.cfg` example

```yaml
[inventory]
enable_plugins = freeformz.ansible.tailscale

[defaults]
inventory = ./inventory/tailscale.yaml
```

Minimal `./inventory/tailscale.yaml` example

```yaml
plugin: freeformz.ansible.tailscale
```

`./inventory/tailscale.yaml` example with defaults

```yaml
plugin: freeformz.ansible.tailscale
include_self: false
ansible_host: ipv4
strip_tag: true
os_groups: true
```

See `ansible-doc -t inventory freeformz.ansible.tailscale` for option documentation.