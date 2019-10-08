import asyncio
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
        self._components = []
        self.handler = default_handler
        self.__start = False
        self._init_components(components)

    def _init_components(self, components):
        for component in components:
            self._add_component(component)

    def _add_component(self, component, position=None):
        if not isinstance(component, Component):
            component = create_component_from(component)
        self._components.insert(position or len(self._components), component)

    add = _add_component  # public version

    def _create_handler(self):
        call_next = _call_next
        for component in self._components[::-1]:
            if component.middleware is not None:
                call_next = partial(component.middleware, call_next=call_next)
                call_next.__code__ = component.middleware.__code__
                call_next.component_name = component.name
        self.handler = partial(call_next, handler=self.handler)

    async def start(self):
        if self.__start:
            return
        self.__start = True
        for component in self._components:
            try:
                await call_or_await(component.start, self)
            except DisableComponentError:
                self._components.remove(component)

            # todo components commands
        self._create_handler()

    async def stop(self):
        if not self.__start:
            return
        for component in self._components:
            await call_or_await(component.stop, self)

    def run(self, port=8000, sub_apps=()):
        run_app(self, port)

    def __getattr__(self, item):
        for component in self._components:
            if component.name == item:
                return component
        raise AttributeError(f"App has no component {item}")


async def _call_next(request, handler):
    return await handler(request)
