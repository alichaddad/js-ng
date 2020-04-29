def export_module_as():

    from jumpscale.core.base import StoredFactory

    from .explorer import Explorer

    return StoredFactory(Explorer)
