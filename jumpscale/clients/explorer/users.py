from jumpscale.core.exceptions import NotFound


class Users:
    def __init__(self, session, url):
        self._session = session
        self._base_url = url
        self._model = j.data.schema.get_from_url("tfgrid.phonebook.user.1")

    def list(self, name=None, email=None):
        query = {}
        if name is not None:
            query["name"] = name
        if email is not None:
            query["email"] = email
        resp = self._session.get(self._base_url + "/users", params=query)
        users = []
        for user_data in resp.json():
            user = self._model.new(datadict=user_data)
            users.append(user)
        return users

    def new(self):
        return self._model.new()

    def register(self, user):
        resp = self._session.post(self._base_url + "/users", json=user._ddict)
        return resp.json()["id"]

    def validate(self, tid, payload, signature):
        url = self._base_url + f"/users/{tid}/validate"
        data = {
            "payload": payload,
            "signature": signature,
        }

        resp = self._session.post(url, json=data)
        return resp.json()["is_valid"]

    def update(self, user, identity=None):
        me = identity if identity else j.tools.threebot.me.default
        datatosign = ""
        datatosign += f"{user.id}{user.name}{user.email}"
        if user.host:
            datatosign += user.host
        datatosign += f"{user.description}{user.pubkey}"
        signature = me.nacl.sign_hex(datatosign.encode("utf8"))
        data = user._ddict.copy()
        data["sender_signature_hex"] = signature.decode("utf8")
        self._session.put(self._base_url + f"/users/{user.id}", json=data)

    def get(self, tid=None, name=None, email=None):
        if tid is not None:
            resp = self._session.get(self._base_url + f"/users/{tid}")
            return self._model.new(datadict=resp.json())

        results = self.list(name=name, email=email)
        if results:
            return results[0]
        raise NotFound("user not found")
