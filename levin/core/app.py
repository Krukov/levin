import inspect
from functools import partial
from typing import Dict, List, Optional

from .common import Request, Response
from .component import Component, DisableComponentError, create_component_from
from .server import run_app


async def _handler(request: Request):
    return Response(200, body=b"<html><head></head><body>LEVIN</body></html>")


async def _call_next(request, handler):
    return await handler(request)


async def call_or_await(func_or_coro, *args, **kwargs):
    result = func_or_coro(*args, **kwargs)
    if inspect.iscoroutine(result):
        return await result
    return result


class Application:
    def __init__(self, components=(), default_handler=_handler):
        self._components: List[Component] = []
        self._handler = default_handler
        self.handler = None
        self.__start = False
        self._init_components(components)

    def _init_components(self, components):
        for component in components:
            self._add_component(component)

    def _add_component(self, component, position=None):
        if isinstance(component, str):
            pass
        if not isinstance(component, Component):
            component = create_component_from(component)
        self._components.insert(position or len(self._components), component)
        component.init(self)

    add = _add_component  # public version

    def _create_handler(self, handler):
        call_next = _call_next
        for component in self._components[::-1]:
            if component.middleware is not None:
                call_next = partial(component.middleware, call_next=call_next)
                call_next.component_name = component.name
        self.handler = partial(call_next, handler=handler)

    async def start(self):
        if self.__start:
            return
        self.__start = True
        _components_to_remove = []
        for component in self._components:
            try:
                await call_or_await(component._start, self)  # pylint: disable=protected-access
            except DisableComponentError:
                _components_to_remove.append(component)
        for component in _components_to_remove:
            self._components.remove(component)

        self._create_handler(self._handler)

    async def stop(self):
        if not self.__start:
            return
        for component in self._components:
            await call_or_await(component.stop, self)

    def run(self, host="0.0.0.0", port=8000, ssl=None):
        run_app(self, host, port=port, ssl=ssl)

    def configure(self, config: Dict):
        for component_name, config_ in config.items():
            component = self.get_component(component_name)
            if not component:
                raise ValueError(f"Wrong component name {component_name}")
            component.configure(**config_)

    def get_component(self, component: str) -> Optional[Component]:
        for _component in self._components:
            if _component.name == component:
                return _component
        return None

    @property
    def components(self):
        return list(self._components)

    def __getattr__(self, item):
        for component in self._components:
            if component.name == item:
                return component
        raise AttributeError(f"App has no component {item}")
