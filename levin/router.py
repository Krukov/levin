import re
from typing import Callable, Dict, List, Tuple, Union

from . import typing

PATH_ARG = re.compile(br"{(?P<name>[-_a-zA-Z]+)}")
PATH_REPL = br"(?P<\g<name>>[-_a-zA-Z]+)"
BACK_PATH_ARG = re.compile(br"\(\?P<(?P<name>[-_a-zA-Z]+)[^/]+\)")
BACK_PATH_REPL = br"{\g<name>}"


class RegexpCondition:
    def __init__(self, method: bytes, pattern: typing.Pattern):
        self.method = method
        if isinstance(pattern, str):
            pattern = pattern.encode()
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
            return {**match.groupdict(), "pattern": self.pattern}

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
    def __init__(self, method: bytes, pattern: typing.Pattern):
        if isinstance(pattern, str):
            pattern = pattern.encode()
        self.method = method
        self.pattern = pattern

    def __call__(self, request: typing.Request) -> Union[bool, Dict]:
        if self.method == request.method and self.slash_append(self.pattern) == self.slash_append(request.path):
            return {"pattern": self.pattern}

    @staticmethod
    def slash_append(value: bytes) -> bytes:
        if not value.endswith(b"/"):
            value += b"/"
        return value


class HttpRouter:
    def __init__(self):
        self._routes: List[Tuple[List[Callable[[typing.Request], Union[bool, Dict]]], Callable]] = []

    def resolve(self, request: typing.Request) -> Union[None, Callable]:
        for conditions, handler in self._routes:
            conditions_result = [condition(request) for condition in conditions]
            if not all(conditions_result):
                continue

            for condition_result in conditions_result:
                if not isinstance(condition_result, dict):
                    continue
                for key, value in condition_result.items():
                    request[key] = value
            return handler

    def add(self, method: Union[str, bytes], pattern: typing.Pattern, handler: Callable):
        if isinstance(method, str):
            method = method.encode()
        if isinstance(pattern, str):
            pattern = pattern.encode()
        if isinstance(pattern, typing.CompiledRe) or b"{" in pattern:
            self._routes.append(([RegexpCondition(method, pattern)], handler))
        else:
            self._routes.append(([EqualsCondition(method, pattern)], handler))
