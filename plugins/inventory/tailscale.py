import json
import ipaddress
import socket

from datetime import datetime, timedelta
from ansible.module_utils.urls import Request

# try:
#    from __main__ import display
# except ImportError:
#    from ansible.utils.display import Display
#    display = Display()

__metaclass__ = type


DOCUMENTATION = """
    name: tailscale
    plugin_type: inventory
    short_description: Tailscale Inventory Source
    extends_documentation_fragment:
        - constructed
    description: Get hosts from a Tailscale tailnet using the Tailscale API - https://github.com/tailscale/tailscale/blob/main/api.md#tailnet-devices
    options:
        plugin:
            description: token to ensure this is a source file for the 'tailscale' plugin.
            required: True
            choices: ['freeformz.ansible.tailscale']
        api_key:
            description: API key to use. Can also be a jinja2 template to get the key from another source, like the token endpoint with OAuth credentials.
            type: string
            required: true
        tailnet:
            description: Tailnet that we should use.
            type: string
            required: true
        include_self:
            description: Include this system in the inventory?
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
        tailscale_domain:
            description: The tailscale domain to use when constructing a fully qualified hostname.
            type: string
            default: "beta.tailscale.net"
            required: false
        include_online_offline_groups:
            description: Include online/offline groups?
            type: bool
            default: True
            required: false
        online_timeout:
            description: Timeout, in minutes, used to determine when a host is considered "offline" when no latency information is returned by the api.
            type: int
            default: 10
            required: false
        tag_groups:
            description: Create groups for labels?.
            type: bool
            default: true
            required: false
"""

EXAMPLES = """
plugin: freeformz.ansible.tailscale
api_key: '{{ lookup("pipe", "./scripts/get-tailscale-api-token") }}'
tailnet: my.tailnet
include_self: false
ansible_host: host_name
strip_tag: true
os_groups: true
tailscale_domain: beta.tailscale.net
include_online_offline_groups: true
online_timeout: 10
tag_groups: false
"""

from ansible.plugins.inventory import BaseInventoryPlugin, Constructable


def strip_tag(tag):
    return tag.removeprefix("tag:")


def safe_tag(tag):
    return tag.replace(":", "_").replace("-", "_")


def map_name(name):
    n = []
    last_upper = False
    for c in name:
        if not c.isupper():
            last_upper = False
            n.append(c)
            continue
        if not last_upper:
            n.append("_")
        n.append(c.lower())
        last_upper = True
    return "".join(n)


def map_dict(d):
    if not type(d) is dict:
        return d
    nd = {}
    for k, v in d.items():
        k = map_name(k)
        if type(v) is dict:
            nd[map_name(k)] = map_dict(v)
        else:
            nd[map_name(k)] = v
    return nd


class TailscaleHost:
    def __init__(self, hostname, id, data):
        self.name = hostname
        self.id = id
        self.data = data

    def ipv4(self):
        for address in self.data["addresses"]:
            addr = ipaddress.ip_address(address)
            if addr.__class__ == ipaddress.IPv4Address:
                return address

    def ipv6(self):
        for address in self.data["addresses"]:
            addr = ipaddress.ip_address(address)
            if addr.__class__ == ipaddress.IPv6Address:
                return address

    def is_self(self):
        hn = socket.gethostname().split(".")[0]
        return self.name == hn

    def online(self, timeout):
        latency = self.data.get("clientConnectivity", {}).get("latency", {})
        if len(latency) > 0:
            return True

        # 2022-07-13T09:29:56Z
        last_seen = self.data.get("lastSeen", None)
        try:
            last_seen = datetime.strptime(last_seen, "%Y-%m-%dT%H:%M:%SZ")
        except:
            return False

        now = datetime.utcnow()

        return (now - last_seen) <= timeout


class TailscaleAPI:
    """
    {
        "devices": [
            {
                "addresses": [
                    "100.92.75.96",
                    "fd7a:115c:a1e0:ab12:4843:cd96:625c:4b60"
                ],
                "id": "1343255325539688",
                "user": "freeformz@github",
                "name": "linode-1.freeformz.github",
                "hostname": "li1196-33",
                "clientVersion": "1.24.2-t9d6867fb0-g2d0f7ddc3",
                "updateAvailable": true,
                "os": "linux",
                "created": "2021-08-07T22:26:07Z",
                "lastSeen": "2022-07-18T20:44:31Z",
                "keyExpiryDisabled": true,
                "expires": "2022-02-03T22:26:07Z",
                "authorized": true,
                "isExternal": false,
                "machineKey": "mkey:632c98c518b8cc0600ee401efdd840abe84f507a6b009e70707897c03193c324",
                "nodeKey": "nodekey:7eba0046551e71ecb8ff87b3a4155b1424abdeb1ff3d035782b408f4c4dc4b5f",
                "blocksIncomingConnections": false,
                "enabledRoutes": [],
                "advertisedRoutes": [],
                "tags": [ "tag:thisisatag" ],
                "clientConnectivity": {
                    "endpoints": [
                        "45.79.97.33:41641",
                        "[2600:3c01::f03c:92ff:fea7:867b]:41641",
                        "172.17.0.1:41641",
                        "172.18.0.1:41641"
                    ],
                    "derp": "",
                    "mappingVariesByDestIP": false,
                    "latency": {
                        "Chicago": {
                            "latencyMs": 50.229614
                        },
                        "Dallas": {
                            "latencyMs": 35.857095
                        },
                        "New York City": {
                            "latencyMs": 70.991985
                        },
                        "San Francisco": {
                            "preferred": true,
                            "latencyMs": 2.570926
                        },
                        "Seattle": {
                            "latencyMs": 22.222779000000003
                        },
                        "Tokyo": {
                            "latencyMs": 107.27332100000001
                        }
                    },
                    "clientSupports": {
                        "hairPinning": false,
                        "ipv6": true,
                        "pcp": false,
                        "pmp": false,
                        "udp": true,
                        "upnp": false
                    }
                }
            },
    ...
    ]
    """

    def __init__(self, api_key, tailnet, remove_tag_prefix=True):
        self.request = Request(
            url_username=api_key,
            url_password="",
            force_basic_auth=True,
        )
        self.tailnet = tailnet
        self.remove_tag_prefix = remove_tag_prefix
        self.refresh()

    def refresh(self):
        res = self.request.get(
            f"https://api.tailscale.com/api/v2/tailnet/{self.tailnet}/devices?fields=all",
        )
        res = json.loads(res.read())
        self.hosts = {}
        self.all_tags = set()
        for host in res["devices"]:
            hostname = host["hostname"]
            del host["hostname"]
            id = host["id"]
            del host["id"]

            tags = host.get("tags", None)
            if tags:
                if self.remove_tag_prefix:
                    tags = list(map(strip_tag, tags))
                tags = list(map(safe_tag, tags))
                host["tags"] = tags
                for tag in host["tags"]:
                    self.all_tags.add(tag)

            self.hosts[hostname] = TailscaleHost(hostname, id, host)


class InventoryModule(BaseInventoryPlugin, Constructable):
    NAME = "freeformz.ansible.tailscale"

    def __init__(self):
        super(InventoryModule, self).__init__()

    def get_inventory(self):
        api_key = self.templar.template(self.get_option("api_key"))
        tailnet = self.get_option("tailnet")
        tailscale = TailscaleAPI(
            api_key, tailnet, remove_tag_prefix=self.get_option("strip_tag")
        )

        online_offline_groups = self.get_option("include_online_offline_groups")
        if online_offline_groups:
            for group in ["online", "offline"]:
                self.inventory.add_group(group)

        if self.get_option("tag_groups"):
            for tag in tailscale.all_tags:
                self.inventory.add_group(tag)

        for _, host in tailscale.hosts.items():
            if not self.get_option("include_self") and host.is_self():
                continue

            hostname = host.name
            mapped_host_name = host.data["name"]
            if mapped_host_name:
                mapped_host_name = mapped_host_name.split(".")[0]
                if mapped_host_name != hostname:
                    hostname = mapped_host_name

            if hostname in self.inventory.hosts:
                continue

            self.inventory.add_host(hostname)
            ipv4 = host.ipv4()
            if ipv4:
                self.inventory.set_variable(hostname, "ipv4", ipv4)
            ipv6 = host.ipv6()
            if ipv6:
                self.inventory.set_variable(hostname, "ipv6", ipv6)

            status = (
                "online"
                if host.online(timedelta(minutes=self.get_option("online_timeout")))
                else "offline"
            )
            self.inventory.set_variable(hostname, "status", status)

            ansible_host = self.get_option("ansible_host")
            if ansible_host == "ipv4":
                self.inventory.set_variable(hostname, "ansible_host", ipv4)
            elif ansible_host == "ipv6":
                self.inventory.set_variable(hostname, "ansible_host", ipv6)
            elif ansible_host == "dns":
                self.inventory.set_variable(hostname, "ansible_host", host.data["name"])
            elif ansible_host == "host_name":
                self.inventory.set_variable(hostname, "ansible_host", hostname)

            if self.get_option("os_groups", True):
                os = host.data["os"].lower()
                if os not in self.inventory.groups:
                    self.inventory.add_group(os)
                self.inventory.add_host(hostname, os)

            tags = host.data.get("tags", None)
            if self.get_option("tag_groups") and tags:
                self.inventory.set_variable(hostname, "tags", tags)
                for tag in tags:
                    if tag not in self.inventory.groups:
                        self.inventory.add_group(tag)
                    self.inventory.add_host(hostname, tag)

            for key, item in host.data.items():
                self.inventory.set_variable(hostname, map_name(key), map_dict(item))

            if online_offline_groups:
                self.inventory.add_host(hostname, status)

            # Use constructed if applicable
            strict = self.get_option('strict')

            # Composed variables
            self._set_composite_vars(self.get_option('compose'), self.inventory.get_host(hostname).get_vars(), hostname, strict=strict)

            # Complex groups based on jinja2 conditionals, hosts that meet the conditional are added to group
            self._add_host_to_composed_groups(self.get_option('groups'), {}, hostname, strict=strict)

            # Create groups based on variable values and add the corresponding hosts to it
            self._add_host_to_keyed_groups(self.get_option('keyed_groups'), {}, hostname, strict=strict)

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

        self.get_inventory()


def main():
    print("TODO")


if __name__ == "__main__":
    main()
