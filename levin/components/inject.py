from functools import partial
import inspect
from typing import TypeVar
from levin.core.common import Request, Response
from levin.core.component import Component


class AddRequest(Component):
    name = "add_request"

    @staticmethod
    def middleware(request: Request, handler, call_next) -> Response:
        if "request" in inspect.signature(handler).parameters:
            handler = partial(handler, request)

        return call_next(request, handler)


class InjectFromScope(Component):
    name = "injector"

    @staticmethod
    def middleware(request: Request, handler, call_next) -> Response:
        params = inspect.signature(handler).parameters
        kwargs = {}
        for param in params.values():
            if hasattr(param.annotation, "_value_name"):
                kwargs[param.name] = request.get(param.annotation._value_name)
        if kwargs:
            handler = partial(handler, **kwargs)
        return call_next(request, handler)

    @staticmethod
    def Inject(value_name: str) -> TypeVar:
        type_container = TypeVar("str", str, str)
        type_container._value_name = value_name
        return type_container
