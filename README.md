# Ansible Bits

Install via: `ansible-galaxy collection install freeformz.ansible`

## Tailscale Inventory Plugin

Requires a tailscale api key.

Creates groups for each tag, each os (when os_groups = true - Defaults to true), and online/offline status (when include_online_offline_groups == true - Defaults to true).

Tags in Tailscale start with `tag:`. This prefix is stripped when `strip_tag` == true (the default), otherwise it is converted to `tag_`.

### Examples

This is a watered down version of the config of my personal home lab tailscale + ansible setup.

`ansible.cfg`

```toml
[inventory]
enable_plugins = freeformz.ansible.tailscale

[defaults]
inventory = ./inventory/tailscale.yaml
```

`./inventory/tailscale.yaml`

```yaml
plugin: freeformz.ansible.tailscale
ansible_host: ipv4
api_key: "<a tailscale api key>"
tailnet: freeformz.github
```

Run `ansible-inventory --list` to see the output. If you are playing with options, you can use this command to see how they affect the inventory.

See `ansible-doc -t inventory freeformz.ansible.tailscale` for more documentation and all the options.
