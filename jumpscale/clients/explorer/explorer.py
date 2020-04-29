import requests
from urllib.parse import urlparse

from .nodes import Nodes
from .users import Users
from .farms import Farms
from .reservations import Reservations
from .errors import raise_for_status

from jumpscale.god import j
from jumpscale.clients.base import Client
from jumpscale.core.base import fields


class Explorer(Client):
    url = fields.String()

    def _init(self, **kwargs):
        # load models
        basepath = "{DIR_CODE}/github/threefoldtech/jumpscaleX_threebot/ThreeBotPackages/tfgrid/{pkgname}/models"
        j.data.schema.add_from_path(j.core.tools.text_replace(basepath, {"pkgname": "workloads"}))
        j.data.schema.add_from_path(j.core.tools.text_replace(basepath, {"pkgname": "phonebook"}))
        j.data.schema.add_from_path(j.core.tools.text_replace(basepath, {"pkgname": "directory"}))
        self._session = requests.Session()
        self._session.hooks = dict(response=raise_for_status)

        self._nodes = None
        self._users = None
        self._farms = None
        self._reservations = None
        self._gateway = None

    @property
    def nodes(self):
        if not self._nodes:
            self._nodes = Nodes(self._session, self.url)
        return self._nodes

    @property
    def users(self):
        if not self._users:
            self._users = Users(self._session, self.url)
        return self._users

    @property
    def farms(self):
        if not self._farms:
            self._farms = Farms(self._session, self.url)
        return self._farms

    @property
    def reservations(self):
        if not self._reservations:
            self._reservations = Reservations(self._session, self.url)
        return self._reservations

    @property
    def gateway(self):
        if self._gateway is None:
            parsedurl = urlparse(self.url)
            gedisclient = j.clients.gedis.get(
                name=f"{self.instance_name}_gateway", hostname=parsedurl.hostname, package_name="tfgrid.gateway"
            )
            self._gateway = gedisclient.actors.gateway
        return self._gateway
