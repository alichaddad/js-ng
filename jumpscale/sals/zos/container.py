import netaddr
from jumpscale.core.exceptions import Input
import base58
from nacl import signing
from .id import _next_workload_id
from nacl import public
import binascii


class Container:
    def create(
        self,
        reservation,
        node_id,
        network_name,
        ip_address,
        flist,
        env={},
        cpu=1,
        memory=1024,
        entrypoint="",
        interactive=False,
        secret_env={},
        public_ipv6=False,
        storage_url="zdb://hub.grid.tf:9900",
    ):
        """Creates and add a container to the reservation

        Args:
            reservation ([type]): reservation object
            node_id (str): id of the node of the container
            network_name (str): identifier of the network
            ip_address (str): container ip address in the network
            flist (str): flist url to start the container with
            env (dict, optional): Environment variables to set. Defaults to {}.
            cpu (int, optional): CPU capacity. Defaults to 1.
            memory (int, optional): Memory capacity. Defaults to 1024.
            entrypoint (str, optional): Container init command. Defaults to "".
            interactive (bool, optional): Specifies interactive contaienr start or not. Defaults to False.
            secret_env (dict, optional): Secret Environment variables to set. Defaults to {}.
            public_ipv6 (bool, optional): IPV6 container ip address in the network. Defaults to False.
            storage_url (str, optional): Server used as storage backend. Defaults to "zdb://hub.grid.tf:9900".

        Raises:
            jumpscale.core.exceptions.Input: If ip not in specified network range

        Returns:
            [type]: container object
        """

        cont = reservation.data_reservation.containers.new()
        cont.node_id = node_id
        cont.workload_id = _next_workload_id(reservation)

        cont.flist = flist
        cont.storage_url = storage_url
        cont.environment = env
        cont.secret_environment = secret_env
        cont.entrypoint = entrypoint
        cont.interactive = interactive

        nw = None
        for nw in reservation.data_reservation.networks:
            if nw.name == network_name:
                ip = netaddr.IPAddress(ip_address)
                subnet = netaddr.IPNetwork(nw.iprange)
                if ip not in subnet:
                    raise Input(
                        f"ip address {str(ip)} is not in the range of the network resource of the node {str(subnet)}"
                    )

        net = cont.network_connection.new()
        net.network_id = network_name
        net.ipaddress = ip_address
        net.public_ip6 = public_ipv6

        cont.capacity.cpu = cpu
        cont.capacity.memory = memory

        return cont

    def encrypt_secret(self, node_id, value):
        key = base58.b58decode(node_id)
        pk = signing.VerifyKey(key)
        encryption_key = pk.to_curve25519_public_key()

        box = public.SealedBox(encryption_key)
        result = box.encrypt(value.encode())

        return binascii.hexlify(result).decode()
