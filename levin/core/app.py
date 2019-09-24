import asyncio
from functools import partial

from levin.core.common import Request, Response
from levin.core.component import Component, DisableComponentError, create_component_from


async def _handler(request: Request):
    return Response(200, body=b"<html><head></head><body>LEVIN</body></html>")


async def call_or_await(func_or_coro, *args, **kwargs):
    result = func_or_coro(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return result


class Application:
    def __init__(self, components, default_handler=_handler):
        self.__components = components
        self._components = {}
        self.handler = default_handler
        self.__start = False

    async def start(self):
        if self.__start:
            return
        self.__start = True
        for component in self.__components:
            if not isinstance(component, Component):
                component = create_component_from(component)
            try:
                await call_or_await(component.start, self)
            except DisableComponentError:
                continue
            if component.name in self._components:
                raise Exception(component.name)
            self._components[component.name] = component
            if component.middleware is not None:
                self.handler = partial(component.middleware, handler=self.handler)
            # todo components commands

    async def stop(self):
        if not self.__start:
            return
        for component in self._components.values():
            await call_or_await(component.stop, self)
