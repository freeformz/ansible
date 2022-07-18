import json
import platform
import subprocess

__metaclass__ = type

DOCUMENTATION = """
    name: tailscale
    plugin_type: inventory
    short_description: Tailscale Inventory Source
    extends_documentation_fragment:
        - constructed
    description: Get inventory hosts from current Tailscale tailnet.
    options:
        plugin:
            description: token to ensure this is a source file for the 'tailscale' plugin.
            required: True
            choices: ['freeformz.ansible.tailscale']
        include_self:
            description: Include this system in the output?
            type: bool
            required: false
            default: false
        ansible_host:
            description: set the ansible_host to which value?
            required: false
            choices: ['ipv4','ipv6','dns','host_name']
            default: host_name
        strip_tag:
            description: strip the tag colon prefix from the start of tags
            type: bool
            default: True
            required: false
        os_groups:
            description: create groups for each os?
            type: bool
            default: True
            required: false
"""

EXAMPLES = """
plugin: freeformz.ansible.tailscale
include_self: false
ansible_host: ipv4
strip_tag: true
os_groups: true
"""

from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Templar


def strip_tag(tag):
    return tag.removeprefix("tag:")


def tailscale_cli():
    tailscale_cmd = "tailscale"
    if platform.system() == "Darwin":
        tailscale_cmd = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
    return tailscale_cmd


def tailscale_status():
    proc = subprocess.run([tailscale_cli(), "status", "--json"], capture_output=True)
    return json.loads(proc.stdout)


def tailscale_ipv4(host):
    proc = subprocess.run([tailscale_cli(), "ip", "-4", host], capture_output=True)
    return proc.stdout.strip().decode("utf-8")


def tailscale_ipv6(host):
    proc = subprocess.run([tailscale_cli(), "ip", "-6", host], capture_output=True)
    return proc.stdout.strip().decode("utf-8")


class InventoryModule(BaseInventoryPlugin, Constructable):

    VARIABLE_MAPPINGS = {
        "OS": "os",
        "ID": "id",
        "PublicKey": "public_key",
        "UserID": "user_id",
        "TailscaleIPs": "tailscale_ips",
        "Relay": "relay",
        "RxBytes": "rx_bytes",
        "TxBytes": "tx_bytes",
        "Created": "created",
        "LastWrite": "last_write",
        "LastSeen": "last_seen",
        "LastHandshake": "last_handshake",
        "Online": "online",
        "KeepAlive": "keep_alive",
        "ExitNode": "exit_node",
        "ExitNodeOption": "exit_node_option",
        "Active": "active",
        "sshHostKeys": "ssh_host_keys",
        "InNetworkMap": "in_network_map",
        "InMagicSock": "in_magic_sock",
        "InEngine": "in_engine",
        "Addrs": "addresses",
        "PeerAPIURL": "peer_api_url",
        "Capabilities": "capabilities",
    }

    NAME = "freeformz.ansible.tailscale"

    def __init__(self):
        super(InventoryModule, self).__init__()

    def get_inventory(self):
        tailscale_json = tailscale_status()

        all_hosts = list(
            tailscale_json["Peer"].values(),
        )
        if self.config.get("include_self", False):
            all_hosts.append(
                tailscale_json["Self"],
            )

        for h in all_hosts:
            host_name = h["HostName"]
            if host_name not in self.inventory.hosts:
                self.inventory.add_host(host_name)
                ipv4 = tailscale_ipv4(host_name)
                self.inventory.set_variable(host_name, "ipv4", ipv4)
                ipv6 = tailscale_ipv6(host_name)
                self.inventory.set_variable(host_name, "ipv6", ipv6)

                ansible_host = self.config.get("ansible_host", "ipv4")
                if ansible_host == "ipv4":
                    self.inventory.set_variable(host_name, "ansible_host", ipv4)
                elif ansible_host == "ipv6":
                    self.inventory.set_variable(host_name, "ansible_host", ipv6)
                elif ansible_host == "dns":
                    self.inventory.set_variable(host_name, "ansible_host", h["DNSName"].removesuffix("."))
                elif ansible_host == "host_name":
                    self.inventory.set_variable(host_name, "ansible_host", host_name)

                for variable in self.VARIABLE_MAPPINGS:
                    if variable in h:
                        self.inventory.set_variable(
                            host_name, self.VARIABLE_MAPPINGS[variable], h[variable]
                        )

            state = "online" if h["Online"] else "offline"
            if state not in self.inventory.groups:
                self.inventory.add_group(state)
            self.inventory.add_host(host_name, state)

            if self.config.get("os_groups", True):
                os = h["OS"]
                if os not in self.inventory.groups:
                    self.inventory.add_group(os)
                self.inventory.add_host(host_name, os)

            if "Tags" in h:
                tags = h["Tags"]
                if self.config.get("strip_tag", True):
                    tags = list(map(strip_tag, tags))
                self.inventory.set_variable(host_name, "tags", tags)
                for tag in tags:
                    safe_tag = tag.replace(":", "_")
                    if safe_tag not in self.inventory.groups:
                        self.inventory.add_group(safe_tag)
                    self.inventory.add_host(host_name, safe_tag)

    def verify_file(self, path):
        """
        :param path: the path to the inventory config file
        :return the contents of the config file
        """
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(("tailscale.yaml", "tailscale.yml")):
                return True
        return False

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        self.config = self._read_config_data(path)
        self.loader = loader
        self.inventory = inventory
        self.templar = Templar(loader=loader)

        self.get_inventory()
