import asyncio
import sys
import types
from functools import partial

from .common import Request, Response
from .component import Component, DisableComponentError, create_component_from
from .server import run_app


async def _handler(request: Request):
    return Response(200, body=b"<html><head></head><body>LEVIN</body></html>")


async def call_or_await(func_or_coro, *args, **kwargs):
    result = func_or_coro(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return result


class Application:
    def __init__(self, components, default_handler=_handler):
        self.__components = self._init_components(components)
        self._components = {}
        self.handler = default_handler
        self.__start = False

    @staticmethod
    def _init_components(components):
        _components = {}

        for component in components:
            if not isinstance(component, Component):
                component = create_component_from(component)
            if component.name in _components:
                raise Exception(component.name)
            _components[component.name] = component
        return _components

    def _create_handler(self):
        call_next = _call_next
        for component in list(self._components.values())[::-1]:
            if component.middleware is not None:
                call_next = partial(component.middleware, call_next=call_next)
        self.handler = partial(call_next, handler=self.handler)

    async def start(self):
        if self.__start:
            return
        self.__start = True
        for component in list(self.__components.values()):
            try:
                await call_or_await(component.start, self)
            except DisableComponentError:
                continue
            self._components[component.name] = component

            # todo components commands
        self._create_handler()

    async def stop(self):
        if not self.__start:
            return
        for component in self._components.values():
            await call_or_await(component.stop, self)

    def run(self, port):
        run_app(self, port)

    def __getattr__(self, item):
        if item in self.__components:
            return self.__components[item]
        raise AttributeError(f"App has no component {item}")


async def _call_next(request, handler):
    return await handler(request)


class AppComponentFinder:
    def __init__(self, app):
        self._app = app

    def find_module(self, fullname, path=None):
        print(fullname, path)
        return self

    def load_module(self, fullname):
        if fullname in sys.modules:
            # Do nothing, just return None. This likely breaks the idempotency
            # of import statements, but again, in the interest of being brief,
            # we skip this part.
            return

        m = types.ModuleType(fullname, "This is the doc string for the module")
        m.__file__ = "<tmp {}>".format("")
        m.__name__ = fullname
        m.__loader__ = self
        sys.modules[fullname] = m

        return m


def init_app_component_imports(app):
    sys.meta_path.append(AppComponentFinder(app))
