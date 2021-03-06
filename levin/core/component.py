import inspect
from typing import Awaitable, Callable, Optional, Union


class DisableComponentError(Exception):
    pass


class Component:
    name: str = __name__
    middleware: Optional[Union[Callable, Awaitable]] = None

    enable: bool = True

    def __init__(self, **kwargs):
        self.configure(**kwargs)

    def init(self, app):
        pass

    def configure(self, **kwargs):
        for param in self.get_configure_params():
            if param in kwargs:
                setattr(self, param, kwargs.get(param))

    def get_configure_params(self):
        for param in vars(self.__class__):
            allow_name = param.startswith("_") or param in ("name", "middleware")
            if (
                allow_name
                or isinstance(getattr(self.__class__, param), property)
                or inspect.ismethod(getattr(self, param))
            ):
                continue
            yield param
        yield "enable"

    def start(self, app):
        pass

    def _start(self, app):
        if not self.enable:
            raise DisableComponentError()
        return self.start(app)

    def stop(self, app):
        pass


class MiddlewareComponent(Component):
    on_start = None
    on_stop = None
    middleware = None

    def __init__(self, middleware, name=None, **kwargs):
        self.middleware = middleware
        self.name = name or middleware.__name__
        super().__init__(**kwargs)

    def start(self, app):
        if callable(self.on_start):
            self.on_start(app)  # pylint: disable=not-callable

    def stop(self, app):
        if callable(self.on_stop):
            self.on_stop(app)  # pylint: disable=not-callable


def create_component_from(middleware, on_start=None, on_stop=None, name=None):
    return MiddlewareComponent(middleware=middleware, on_start=on_start, on_stop=on_stop, name=name)
