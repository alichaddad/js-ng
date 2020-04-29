from .container import Container
from .kubernetes import Kubernetes
from .network import Network
from .node_finder import NodeFinder
from .volumes import Volumes
from .zdb import ZDB
from .billing import Billing
from .gateway import Gateway
from jumpscale.data.time import now
from jumpscale.data.serializers.json import dump_to_file, load_from_file
from jumpscale.data.nacl import payload_build
from jumpscale.god import j


class Zosv2:
    def __init__(self):
        self._explorer = j.clients.explorer.get("default")
        self._nodes_finder = NodeFinder(self._explorer)
        self._network = Network(self._explorer)
        self._container = Container()
        self._volume = Volumes()
        self._zdb = ZDB(self._explorer)
        self._kubernetes = Kubernetes(self._explorer)
        self._billing = Billing(self._explorer)
        self._gateway = Gateway(self._explorer)

    @property
    def network(self):
        return self._network

    @property
    def container(self):
        return self._container

    @property
    def volume(self):
        return self._volume

    @property
    def zdb(self):
        return self._zdb

    @property
    def kubernetes(self):
        return self._kubernetes

    @property
    def nodes_finder(self):
        return self._nodes_finder

    @property
    def billing(self):
        return self._billing

    def reservation_create(self):
        """Creates a new empty reservation schema

        Returns:
            [type]: reservation object
        """
        return self._explorer.reservations.new()

    def reservation_register(
        self, reservation, expiration_date, identity=None, expiration_provisioning=None, customer_tid=None
    ):
        """register a reservation in BCDB.
           If expiration_provisioning is specified and the reservation is not provisioning before expiration, it will never be provionned.

        Args:
            reservation ([type]): reservation object
            expiration_date (int): timestamp of the date when to expiration should expire
            identity ([type], optional): Threebot me identity to use. Defaults to None.
            expiration_provisioning ([type], optional): timestamp of the date when to reservation should be provisionned. Defaults to None.
            customer_tid (int, optional): Customer threebot id. Defaults to None.

        Returns:
            int: reservation ID
        """
        me = identity if identity else j.tools.threebot.me.default
        reservation.customer_tid = me.tid

        if expiration_provisioning is None:
            expiration_provisioning = now().timestamp + (3600 * 24 * 365)

        dr = reservation.data_reservation

        dr.expiration_provisioning = expiration_provisioning
        dr.expiration_reservation = expiration_date
        dr.signing_request_delete.quorum_min = 0
        dr.signing_request_provision.quorum_min = 0

        # make the reservation cancellable by the user that registered it
        dr.signing_request_delete.signers.append(me.tid)
        dr.signing_request_delete.quorum_min = len(dr.signing_request_delete.signers)

        reservation.json = dr._json
        reservation.customer_signature = me.nacl.sign_hex(reservation.json.encode())

        reservation_id = self._explorer.reservations.create(reservation)
        return reservation_id

    def reservation_accept(self, reservation, identity=None):
        """A farmer need to use this function to notify he accepts to deploy the reservation on his node

        Args:
            reservation ([type]): reservation object
            identity ([type], optional): Threebot me identity to use. Defaults to None.

        Returns:
            bool: true if succeeded,raise an exception otherwise
        """
        me = identity if identity else j.tools.threebot.me.default

        reservation.json = reservation.data_reservation._json
        signature = me.nacl.sign_hex(reservation.json.encode())
        # TODO: missing sign_farm
        # return self._explorer.reservations.sign_farmer(reservation.id, me.tid, signature)

    def reservation_result(self, reservation_id):
        """returns the list of workload provisioning results of a reservation

        Args:
            reservation_id (int): reservation ID

        Returns:
            list: list of worloads results
        """
        return self.reservation_get(reservation_id).results

    def reservation_get(self, reservation_id):
        """fetch a specific reservation from BCDB

        Args:
            reservation_id (int): reservation ID

        Returns:
            [type]: reservation object
        """
        return self._explorer.reservations.get(reservation_id)

    def reservation_cancel(self, reservation_id, identity=None):
        """Cancel a reservation.

           You can only cancel your own reservation
           Once a reservation is cancelled, it is marked as to be deleted in BCDB
           the 0-OS node then detects it and will decomission the workloads from the reservation

        Args:
            reservation_id ([type]): reservation ID
            identity ([type], optional): Threebot me identity to use. Defaults to None.

        Returns:
            bool: true if the reservation has been cancelled successfully
        """
        me = identity if identity else j.tools.threebot.me.default

        reservation = self.reservation_get(reservation_id)
        payload = payload_build(reservation.id, reservation.json.encode())
        signature = me.nacl.sign_hex(payload)

        return self._explorer.reservations.sign_delete(reservation_id=reservation_id, tid=me.tid, signature=signature)

    def reservation_list(self, tid=None):
        """List reservation of a threebot

        Args:
            tid (int, optional): Threebot id. Defaults to None.

        Returns:
            list: list of reservations
        """
        tid = tid if tid else j.tools.threebot.me.default.tid
        result = self._explorer.reservations.list()
        return list(filter(lambda r: r.customer_tid == tid, result))

    def reservation_store(self, reservation, path):
        """Write the reservation on disk.
           Use reservation_load() to load it back

        Args:
            reservation ([type]): reservation object
            path (str): path to write json data to
        """
        dump_to_file(path, reservation._ddict)

    def reservation_load(self, path):
        """load a reservation stored on disk by reservation_store

        Args:
            path (str): source file

        Returns:
            [type]: reservation object
        """
        r = load_from_file(path)
        reservation_model = j.data.schema.get_from_url("tfgrid.workloads.reservation.1")
        return reservation_model.new(datadict=r)

    def reservation_failed(self, reservation):
        """checks if reservation failed

        Args:
            reservation ([type]): reservation object

        Returns:
            [type]: True if any result is in error
        """
        return any(map(lambda x: x == "ERROR", [x.state for x in reservation.results]))

    def reservation_ok(self, reservation):
        """checks if reservation succeeded

        Args:
            reservation ([type]): reservation object

        Returns:
            [type]: True if all results are ok
        """

        return all(map(lambda x: x == "OK", [x.state for x in reservation.results]))

    def _escrow_to_qrcode(self, escrow_address, total_amount, message="Grid resources fees"):
        """Converts escrow info to qrcode

        Args:
            escrow_address (str): escrow address
            total_amount (float): total amount of the escrow
            message (str, optional): message encoded in the qr code. Defaults to "Grid resources fees".

        Returns:
            [type]: [description]
        """
        qrcode = f"tft:{escrow_address}?amount={total_amount}&message={message}&sender=me"
        return qrcode

    def reservation_escrow_information_with_qrcodes(self, reservation_create_resp):
        """Extracts escrow information from reservation create response as a dict and adds qrcode to it
        Sample output:
        [
        {
            'escrow_address': 'GACMBAK2IWHGNTAG5WOVELJWUTPOXA2QY2Y23PAXNRKOYFTCBWICXNDO',
            'total_amount': 0.586674,
            'farmer_id': 10,
            'qrcode': 'tft:GACMBAK2IWHGNTAG5WOVELJWUTPOXA2QY2Y23PAXNRKOYFTCBWICXNDO?amount=0.586674&message=Grid resources fees for farmer 10&sender=me'
        }
        ]

        Args:
            reservation_create_resp ([type]): reservation create object, returned from reservation_register

        Returns:
            str: escrow encoded for QR code usage
        """
        PAYMENT_MSG_TEMPLATE = "Grid resources fees for farmer {}"
        results = []
        for escrow in reservation_create_resp.escrow_information:
            d = escrow._ddict
            escrow_address = escrow.escrow_address
            total_amount = escrow.total_amount / 10e6
            farmer_id = escrow.farmer_id
            d["total_amount"] = total_amount
            # should we include farmer id in the message?
            d["qrcode"] = self._escrow_to_qrcode(escrow_address, total_amount, PAYMENT_MSG_TEMPLATE.format(farmer_id))
            results.append(d)
        return results
