from jumpscale.data.time import now
from jumpscale.data.serializers.json import dumps
from .pagination import get_page, get_all


class Reservations:
    def __init__(self, session, url):
        self._session = session
        self._base_url = url + "/reservations"
        self._model = j.data.schema.get_from_url("tfgrid.workloads.reservation.1")

    def new(self):
        return self._model.new()

    def create(self, reservation):
        resp = self._session.post(self._base_url, json=reservation._ddict)
        return resp.json()

    def list(self, customer_tid=None, next_action=None, page=None):
        if page:
            query = {}
            if customer_tid:
                query["customer_tid"] = customer_tid
            if next_action:
                query["next_action"] = next_action
            reservations, _ = get_page(self._session, page, self._model, self._base_url, query)
        else:
            reservations = list(self.iter(customer_tid, next_action))
        return reservations

    def iter(
        self, customer_tid=None, next_action=None,
    ):
        query = {}
        if customer_tid:
            query["customer_tid"] = customer_tid
        if next_action:
            query["next_action"] = next_action
        yield from get_all(self._session, self._model, self._base_url, query)

    def get(self, reservation_id):
        url = self._base_url + f"/{reservation_id}"
        resp = self._session.get(url)
        return self._model.new(datadict=resp.json())

    def sign_provision(self, reservation_id, tid, signature):
        url = self._base_url + f"/{reservation_id}/sign/provision"
        data = dumps({"signature": signature, "tid": tid, "epoch": now().timestamp})
        self._session.post(url, data=data)
        return True

    def sign_delete(self, reservation_id, tid, signature):
        url = self._base_url + f"/{reservation_id}/sign/delete"
        data = dumps({"signature": signature, "tid": tid, "epoch": now().timestamp})
        self._session.post(url, data=data)
        return True
