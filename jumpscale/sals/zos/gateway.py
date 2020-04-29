import netaddr
from jumpscale.core.exceptions import Input


class Gateway:
    def __init__(self, explorer):
        self._explorer = explorer

    def expose_ip(self, domain, ip):
        """expose_ip configure a TCP proxy to forward traffic
           coming to domain to ip

        Args:
            domain (str): domain name the traffic should be proxied from
            ip (str): address where to forward the traffic

        Raises:
            jumpscale.core.exceptions.Input: [description]
        """
        if not _is_valid_ip(ip):
            raise Input(f"{id} is not valid IP address")

        self._explorer.gateway.tcpservice_ip_register(domain, ip)

    def reverse_tunnel(self, domain, secret):
        """reverse_tunnel configure a TCP proxy in reserve tunnel mode
           use this when your hidden service uses TCP router in reserve tunnel mode
           https://github.com/threefoldtech/tcprouter#reverse-tunneling

        Args:
            domain (secret): domain name the traffic should be proxied from
            secret (secret): secret used by the tcp router client
        """
        self._explorer.gateway.tcpservice_client_register(domain, secret)


def _is_valid_ip(ip):
    try:
        netaddr.IPAddress(ip)
        return True
    except netaddr.AddrFormatError:
        return False
