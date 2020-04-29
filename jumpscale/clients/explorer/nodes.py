from .pagination import get_page, get_all


class Nodes:
    def __init__(self, session, url):
        self._session = session
        self._base_url = url
        self._model = j.data.schema.get_from_url("tfgrid.directory.node.2")

    def _query(self, farm_id=None, country=None, city=None, cru=None, sru=None, mru=None, hru=None, proofs=False):
        query = {}
        if proofs:
            query["proofs"] = "true"
        args = {
            "farm": farm_id,
            "city": city,
            "cru": cru,
            "sru": sru,
            "mru": mru,
            "hru": hru,
        }
        for k, v in args.items():
            if v is not None:
                query[k] = v
        return query

    def list(
        self, farm_id=None, country=None, city=None, cru=None, sru=None, mru=None, hru=None, proofs=False, page=None
    ):

        query = self._query(farm_id, country, city, cru, sru, mru, hru, proofs)
        url = self._base_url + "/nodes"

        if page:
            nodes, _ = get_page(self._session, page, self._model, url, query)
        else:
            nodes = list(self.iter(farm_id, country, city, cru, sru, mru, hru, proofs))

        return nodes

    def iter(self, farm_id=None, country=None, city=None, cru=None, sru=None, mru=None, hru=None, proofs=False):
        query = self._query(farm_id, country, city, cru, sru, mru, hru, proofs)
        url = self._base_url + "/nodes"
        yield from get_all(self._session, self._model, url, query)

    def get(self, node_id, proofs=False):
        params = {}
        if proofs:
            params["proofs"] = "true"
        resp = self._session.get(self._base_url + f"/nodes/{node_id}", params=params)
        return self._model.new(datadict=resp.json())
