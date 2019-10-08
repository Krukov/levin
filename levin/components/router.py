import re
from typing import Callable, Dict, List, Optional, Tuple, Union

from levin import typing
from levin.core.common import Request, Response
from levin.core.component import Component, command, point

PATH_ARG = re.compile(br"{(?P<name>[-_a-zA-Z0-9]+)}")
PATH_REPL = br"(?P<\g<name>>[-_a-zA-Z0-9]+)"
BACK_PATH_ARG = re.compile(br"\(\?P<(?P<name>[-_a-zA-Z0-9]+)[^/]+\)")
BACK_PATH_REPL = br"{\g<name>}"


async def _not_found_handler(request):
    return Response(404, b"Not found")


class RegexpCondition:
    def __init__(self, method: bytes, pattern: typing.Pattern, meta: Dict):
        self.method = method
        self._meta = meta
        if isinstance(pattern, bytes):
            self.pattern = pattern
            self._regexp = self.pattern_to_regexp(self.slash_append(pattern))
        else:
            self._regexp = pattern
            self.pattern = BACK_PATH_ARG.sub(BACK_PATH_REPL, pattern.pattern)

    def __call__(self, request: typing.Request) -> Union[bool, Dict]:
        if self.method != request.method:
            return False
        match = self._regexp.fullmatch(request.path)
        if match:
            return {**match.groupdict(), "pattern": self.pattern, **self._meta}
        return False

    @staticmethod
    def slash_append(value: bytes) -> bytes:
        if not value.endswith(b"/"):
            value += b"/"
        return value + b"?"

    @staticmethod
    def pattern_to_regexp(pattern: bytes) -> typing.CompiledRe:
        pattern = PATH_ARG.sub(PATH_REPL, pattern)
        return re.compile(pattern)


class EqualsCondition:
    def __init__(self, method: bytes, pattern: bytes, meta: Dict):
        self.method = method
        self.pattern = pattern
        self._meta = meta

    def __call__(self, request: Request) -> Union[bool, Dict]:
        if self.method == request.method and self.slash_append(self.pattern) == self.slash_append(request.path):
            return {"pattern": self.pattern, **self._meta}
        return False

    @staticmethod
    def slash_append(value: bytes) -> bytes:
        if not value.endswith(b"/"):
            value += b"/"
        return value


class HttpRouter(Component):
    name = "route"

    def __init__(self, not_found_handler=_not_found_handler):
        self._routes: List[List[Callable[[Request], Union[bool, Dict]], Callable], ...] = []
        self._not_found_handler = not_found_handler

    def clean(self):
        self._routes = []

    def _resolve(self, request: Request) -> Tuple[Callable, Optional[dict]]:
        for condition, handler in self._routes:
            condition_result = condition(request)
            if condition_result:
                return handler, condition_result
        return self._not_found_handler, {}

    @command
    def resolve(self, path: bytes, method: bytes = b"GET"):
        handler, conditions_result = self._resolve(Request(method=method, path=path))
        return handler.__name__

    @point
    def add(self, method: Union[str, bytes], pattern: typing.Pattern, handler: Callable, **meta):
        if isinstance(method, str):
            method = method.encode()
        if isinstance(pattern, str):
            pattern = pattern.encode()
        if isinstance(pattern, typing.CompiledRe) or b"{" in pattern:
            self._routes.append((RegexpCondition(method, pattern, meta), handler))
        else:
            self._routes.append((EqualsCondition(method, pattern, meta), handler))

    @point
    def route(self, path, method="GET", **meta):
        def _decorator(handler):
            self.add(method, path, handler, **meta)
            return handler

        return _decorator

    @point
    def get(self, path, **meta):
        def _decorator(handler):
            self.add("GET", path, handler, **meta)
            return handler

        return _decorator

    @point
    def post(self, path, **meta):
        def _decorator(handler):
            self.add("POST", path, handler, **meta)
            return handler

        return _decorator

    @point
    def put(self, path, **meta):
        def _decorator(handler):
            self.add("PUT", path, handler, **meta)
            return handler

        return _decorator

    @point
    def delete(self, path, **meta):
        def _decorator(handler):
            self.add("DELETE", path, handler, **meta)
            return handler

        return _decorator

    def middleware(self, request, handler, call_next):
        _handler, condition_result = self._resolve(request)
        if isinstance(condition_result, dict):
            for key, value in condition_result.items():
                request.set(key, value)
        return call_next(request, _handler)
