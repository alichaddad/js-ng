"""This module coverts the god object j and its loading process.
the idea is with hierarchy like this
```
project1/
         /rootnamespace (jumpscale)
            /subnamespace1
                ... pkg1
                ... pkg2
            /subnamespace2
                ... pkg1
                ... pkg2
project2/
         /rootnamespace (jumpscale)
            /subnamespace1
                ... pkg1
                ... pkg2
            /subnamespace2
                ... pkg1
                ... pkg2
```
- we get all the paths of the `rootnamespace`
- we get all the subnamespaces
- we get all the inner packages and import all of them (lazily) or load them eagerly but just once.


real example:
```
js-ng
├── jumpscale   <- root namespace
│   ├── clients  <- subnamespace where people can register on
│   │   ├── base.py
│   │   ├── github   <- package in subnamespace
│   │   │   ├── github.py
│   │   │   └── __init__.py
│   │   └── gogs
│   │       ├── gogs.py
│   │       └── __init__.py
│   ├── core
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── data
│   │   ├── idgenerator
│   │   │   ├── idgenerator.py
│   │   │   └── __init__.py
│   │   └── serializers
│   │       ├── __init__.py
│   │       └── serializers.py
│   ├── god.py
│   ├── sals
│   │   └── fs
│   │       ├── fs.py
│   │       └── __init__.py
│   └── tools
│       └── keygen
│           ├── __init__.py
│           └── keygen.py
├── README.md
└── tests
    └── test_loads_j.py
js-ext
├── jumpscale
│   ├── clients
│   │   └── gitlab
│   │       ├── gitlab.py
│   │       └── __init__.py
│   ├── sals
│   │   └── zos
│   │       ├── __init__.py
│   │       └── zos.py
│   └── tools
├── README.md
└── tests
    └── test_success.py
```
"""


import lazy_import
import collections
import importlib
import importlib.util
from jumpscale.core.config import get_config
import os
from pathlib import Path

# import pkgutil
import inspect
import sys
import traceback
from types import SimpleNamespace

__all__ = ["j"]


def namespaceify(mapping):
    if isinstance(mapping, collections.Mapping) and not isinstance(mapping, SimpleNamespace):
        for key, value in mapping.items():
            mapping[key] = namespaceify(value)
        return SimpleNamespace(**mapping)
    return mapping


def loadjsmodules():
    import jumpscale

    loadeddict = {"jumpscale": {}}
    for jsnamespace in jumpscale.__path__:
        for root, dirs, _ in os.walk(jsnamespace):
            for d in dirs:
                if d == "__pycache__":
                    continue
                if os.path.basename(root) == "jumpscale":
                    continue

                if os.path.dirname(root) != jsnamespace:
                    continue
                # print("root: {} d: {}".format(root, d))
                rootbase = os.path.basename(root)
                loadeddict["jumpscale"].setdefault(rootbase, {})
                pkgname = d
                if "noload" in pkgname or pkgname.startswith("."):
                    continue
                importedpkgstr = "jumpscale.{}.{}".format(rootbase, pkgname)
                __all__.append(importedpkgstr)
                #globals()[importedpkgstr] = lazy_import.lazy_module(importedpkgstr)
                
                try:
                    #m = importlib.import_module(importedpkgstr)
                    m = lazy_import.lazy_module(importedpkgstr)
                except Exception as e:
                    traceback.print_exception(*sys.exc_info())
                    print("[-] {} at {} ".format(e, importedpkgstr))
                    continue
                else:
                    if hasattr(m, "export_module_as"):
                        # print("rootbase: ", rootbase, importedpkgstr)
                        # print(m.export_module_as)
                        loadeddict["jumpscale"][rootbase][pkgname] = m.export_module_as
                        # loadeddict[importedpkgstr] = m.export_module_as
                    else:
                        loadeddict["jumpscale"][rootbase][pkgname] = m

    return namespaceify(loadeddict)


class J:
    """
        Here we simulate god object `j` by delegating the calls to suitable subnamespace
    """

    def __init__(self):
        self.__loaded = False

    def __dir__(self):
        self._load()
        return list(self.__loaded_simplenamespace.jumpscale.__dict__.keys()) + ["config", "exceptions", "logger"]

    @property
    def logger(self):
        return self.__loaded_simplenamespace.jumpscale.core.logging

    @property
    def application(self):
        return self.__loaded_simplenamespace.jumpscale.core.application

    @property
    def config(self):
        return self.__loaded_simplenamespace.jumpscale.core.config

    @property
    def exceptions(self):
        return self.__loaded_simplenamespace.jumpscale.core.exceptions

    def reload(self):
        self.__loaded = False
        self.__loaded_simplenamespace = None
        self._load()

    def _locals_get(self, locals_):
        def add(locals_, name, obj):
            if name not in locals_:
                locals_[name] = obj
            return locals_

        # try:
        #     locals_ = add(locals_, "ssh", j.clients.ssh)
        # except:
        #     pass
        # try:
        #     locals_ = add(locals_, "iyo", j.clients.itsyouonline)
        # except:
        #     pass

        # locals_ = add(locals_,"zos",j.kosmos.zos)

        return locals_

    def shell(self, loc: bool = True, exit: bool = True, locals_=None, globals_=None):
        from ptpython.repl import embed
        from .shell.config import ptconfig
        import sys

        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        f = calframe[1]
        if loc:
            print("\n*** file: %s" % f.filename)
            print("*** function: %s [linenr:%s]\n" % (f.function, f.lineno))

        if not locals_:
            locals_ = curframe.f_back.f_locals
        locals_ = self._locals_get(locals_)
        if not globals_:
            globals_ = curframe.f_back.f_globals

        p = Path(f'{os.environ["HOME"]}/.jsx_history')
        if not p.exists():
            p.write_text("")
        history_filename = p.as_posix()

        if exit:
            sys.exit(embed(globals_, locals_, configure=ptconfig, history_filename=history_filename))
        else:
            embed(globals_, locals_, configure=ptconfig, history_filename=history_filename)

    def debug(self):
        import sys
        import pudb
        import threading
        import bdb

        dbg = pudb._get_debugger()

        if isinstance(threading.current_thread(), threading._MainThread):
            pudb.set_interrupt_handler()

        try:
            dbg.set_trace(sys._getframe().f_back, paused=True)
        except bdb.BdbQuit as e:
            # TODO: does not catch it?
            sys.exit()

        sys.exit()

    def _load(self):
        if not self.__loaded:
            self.__loaded_simplenamespace = namespaceify(loadjsmodules())

    def __getattr__(self, name):
        self._load()

        return getattr(self.__loaded_simplenamespace.jumpscale, name)


j = J()
j._load()


# register alerthandler as an error handler
alerts_config = get_config().get("alerts")
if alerts_config and alerts_config.get("enabled", True):
    j.tools.errorhandler.register_handler(
        handler=j.tools.alerthandler.alert_raise, level=alerts_config.get("level", 40)
    )

# register global error hook
sys.excepthook = j.tools.errorhandler.excepthook
