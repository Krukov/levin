from typing import Awaitable, Callable, Optional, Union


class DisableComponentError(Exception):
    pass


class Component:
    name: str = __name__
    middleware: Optional[Union[Callable, Awaitable]] = None

    def __init__(self, *args, **kwargs):
        self.configure(*args, **kwargs)

    def configure(self, *args, **kwargs):
        pass

    def start(self, app):
        pass

    def stop(self, app):
        pass


class MiddlewareComponent(Component):
    def configure(self, middleware, on_start=None, on_stop=None, name=None):
        self._on_start = on_start
        self._on_stop = on_stop
        self.middleware = middleware
        self.name = name or middleware.__name__

    def start(self, app):
        if self._on_start is not None:
            return self._on_start(app)

    def stop(self, app):
        if self._on_stop is not None:
            return self._on_stop(app)


def create_component_from(middleware, on_start=None, on_stop=None, name=None):
    return MiddlewareComponent(middleware, on_start=on_start, on_stop=on_stop, name=name)
