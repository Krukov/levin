from typing import Awaitable, Callable, Optional, Union
import inspect


class DisableComponentError(Exception):
    pass


class Component:
    name: str = __name__
    middleware: Optional[Union[Callable, Awaitable]] = None

    def __init__(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, **kwargs):
        for param in self.get_configure_params():
            if inspect.ismethod(getattr(self, param)):
                continue
            setattr(self, param, kwargs.get(param, getattr(self.__class__, param)))

    @classmethod
    def get_configure_params(cls):
        for param in vars(cls):
            if param.startswith("__") or param in ("name", "middleware"):
                continue
            if isinstance(getattr(cls, param), property):
                continue
            yield param

    def start(self, app):
        pass

    def stop(self, app):
        pass


class MiddlewareComponent(Component):
    _on_start = None
    _on_stop = None
    _name = None
    _middleware = None

    @property
    def middleware(self):
        return self._middleware

    @property
    def name(self):
        return self._name or self.middleware.__name__

    def start(self, app):
        if self._on_start is not None:
            return self._on_start(app)

    def stop(self, app):
        if self._on_stop is not None:
            return self._on_stop(app)


def create_component_from(middleware, on_start=None, on_stop=None, name=None):
    return MiddlewareComponent(_middleware=middleware, on_start=on_start, on_stop=on_stop, _name=name)
