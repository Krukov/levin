from typing import Callable, Optional


class DisableComponentError(Exception):
    pass


def command(method):
    setattr(method, "_command", True)
    return method


def point(method):
    setattr(method, "_point", True)
    return method


class Component:
    name: str = __name__
    middleware: Optional[Callable] = None

    def start(self, app):
        pass

    def stop(self, app):
        pass

    def _get_commands(self):
        for attr in self.__dict__.values():
            if callable(attr) and getattr(attr, "_command"):
                return attr

    def _get_imports(self):
        for attr in self.__dict__.values():
            if callable(attr) and getattr(attr, "_point"):
                return attr

    #
    # @command
    # async def migrate(self):
    #     pass
    #
    # @point
    # async def cache(self, key, value):
    #     pass


class MiddlewareComponent(Component):
    def __init__(self, middleware, on_start=None, on_stop=None, name=None):
        self.__on_start = on_start
        self.__on_stop = on_stop
        self.middleware = middleware
        self.name = name or middleware.__name__

    def start(self, app):
        if self.__on_start is not None:
            return self.__on_start(app)

    def stop(self, app):
        if self.__on_stop is not None:
            return self.__on_stop(app)


def create_component_from(middleware, on_start=None, on_stop=None, name=None):
    return MiddlewareComponent(middleware, on_start=on_start, on_stop=on_stop, name=name)
