import inspect
import re
from typing import Callable, Dict, List, Optional, Tuple, Union

from .cli import command
from levin.core import typing
from levin.core.common import Request, Response
from levin.core.component import Component

PATH_ARG = re.compile(br"{(?P<name>[-_a-zA-Z0-9]+)}")
PATH_REPL = br"(?P<\g<name>>[-_a-zA-Z0-9]+)"
BACK_PATH_ARG = re.compile(br"\(\?P<(?P<name>[-_a-zA-Z0-9]+)[^/]+\)")
BACK_PATH_REPL = br"{\g<name>}"


def _not_found_handler(request):
    return Response(404, b"Not found")


def _slash_append(value: bytes) -> bytes:
    if not value.endswith(b"/"):
        value += b"/"
    return value + b"?"


class RegexpCondition:
    def __init__(self, method: bytes, pattern: typing.Pattern, meta: Dict):
        self.method = method
        self.meta = meta
        if isinstance(pattern, bytes):
            self.pattern = pattern
            self._regexp = self.pattern_to_regexp(_slash_append(pattern))
        else:
            self._regexp = pattern
            self.pattern = BACK_PATH_ARG.sub(BACK_PATH_REPL, pattern.pattern)

    def __call__(self, request: typing.Request) -> Union[bool, Dict]:
        if self.method != request.method:
            return False
        match = self._regexp.fullmatch(request.path)
        if match:
            return {**match.groupdict(), "pattern": self.pattern, **self.meta}
        return False

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
        if self.method == request.method and _slash_append(self.pattern) == _slash_append(request.path):
            return {"pattern": self.pattern, **self._meta}
        return False


class HttpRouter(Component):
    # pylint: disable=too-many-public-methods
    name = "route"

    not_found_handler: Callable = staticmethod(_not_found_handler)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._routes: List[List[Callable[[Request], Union[bool, Dict]], Callable], ...] = []

    def clean(self):
        self._routes = []

    def _resolve(self, request: Request) -> Tuple[Callable, Optional[dict]]:
        for condition, handler in self._routes:
            condition_result = condition(request)
            if condition_result:
                return handler, condition_result
        return self.not_found_handler, {}

    @command
    def resolve(self, path: str, method: str = "GET", code: bool = False):
        """
        Return handler for given path and method
        """
        handler, conditions_result = self._resolve(Request(method=method.encode(), path=path.encode()))
        pattern = ""
        if "pattern" in conditions_result:
            pattern = f"with pattern \"{conditions_result['pattern'].decode()}\""
        base = (
            f'Find handler "{handler.__name__}" {pattern} in '
            f"{inspect.getsourcefile(handler)}:{handler.__code__.co_firstlineno} "
        )
        if code:
            code = inspect.getsource(handler)
            return f"{base}\n\n{code}"
        if inspect.getdoc(handler):
            return f"{base}\n\n{inspect.getdoc(handler)}"
        return base

    @command
    def list(self, method: Optional[str] = None, code: bool = False):
        """
        Return List of routes
        """
        lines = []
        for condition, handler in self._routes:
            if method and condition.method != method:
                continue
            lines.append(
                f"{condition.method.decode()} {condition.pattern.decode()} -> {handler.__name__} "
                f"in {inspect.getsourcefile(handler)}:{handler.__code__.co_firstlineno}"
            )
            if code:
                lines.append(inspect.getsource(handler))
        return "\n".join(lines)

    def add(self, method: Union[str, bytes], pattern: typing.Pattern, handler: Callable, **meta):
        if isinstance(method, str):
            method = method.encode()
        if isinstance(pattern, str):
            pattern = pattern.encode()
        if isinstance(pattern, typing.CompiledRe) or b"{" in pattern:
            self._routes.append((RegexpCondition(method, pattern, meta), handler))
        else:
            self._routes.append((EqualsCondition(method, pattern, meta), handler))

    def url(self, name, **kwargs):
        for condition, _ in self._routes:
            if condition.meta.get("name", "") == name:
                return condition.pattern.decode().replace("\\", "").format(**kwargs)
        raise ValueError("Unknown url")

    def route(self, path, method="GET", **meta):
        def _decorator(handler):
            self.add(method, path, handler, **meta)
            return handler

        return _decorator

    def get(self, path, **meta):
        def _decorator(handler):
            self.add("GET", path, handler, **meta)
            return handler

        return _decorator

    def post(self, path, **meta):
        def _decorator(handler):
            self.add("POST", path, handler, **meta)
            return handler

        return _decorator

    def put(self, path, **meta):
        def _decorator(handler):
            self.add("PUT", path, handler, **meta)
            return handler

        return _decorator

    def delete(self, path, **meta):
        def _decorator(handler):
            self.add("DELETE", path, handler, **meta)
            return handler

        return _decorator

    def middleware(self, request, handler, call_next):
        request.set("get_url", self.url, lazy=False)
        request.set("get_route", self._resolve, lazy=False)
        _handler, condition_result = self._resolve(request)
        if isinstance(condition_result, dict):
            for key, value in condition_result.items():
                request.set(key, value)
        return call_next(request, _handler)
