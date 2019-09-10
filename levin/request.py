from types import MappingProxyType
from typing import Mapping, Tuple

CONTENT_TYPE_HEADER = b"content-type"
empty = object()

DEFAULT_ENCODING = "iso-8859-1"


class HeadersProxy:
    __slots__ = ("__target", )

    def __init__(self, target: Mapping):
        self.__target = target

    def __getitem__(self, item: bytes):
        return self.__target[item.lower()]

    def __len__(self):
        return len(self.__target)

    def get(self, item: bytes):
        return self.__target.get(item.lower())

    def __contains__(self, item: bytes):
        return item.lower() in self.__target


def create_headers_map(headers: Tuple) -> HeadersProxy:
    _headers = {}
    for name, value in headers:
        _headers.setdefault(name.lower(), []).append(value)
    return HeadersProxy(MappingProxyType({name: b"; ".join(value) for name, value in _headers.items()}))


class Request:
    __slots__ = ("path", "method", "_body", "_typed_body", "headers", "_scope", "stream")

    def __init__(
        self, path: bytes = b"/", method: bytes = b"GET", body: bytes = b"", headers: Tuple = (), stream: int = 0
    ):
        self.path = path
        self.method = method
        self._body = body
        self.headers = create_headers_map(headers)
        self._typed_body: str = empty
        self._scope = {}
        self.stream = stream

    def __getitem__(self, item):
        return self._scope.get(item)

    def __setitem__(self, key, value):
        self._scope[key] = value

    @property
    def content_type(self) -> bytes:
        content_type = self.headers.get(CONTENT_TYPE_HEADER)
        if content_type:
            return content_type.split(b";", 1)[0]

    @property
    def encoding(self) -> str:
        content_type = self.headers.get(CONTENT_TYPE_HEADER)
        if not content_type or b";" not in content_type:
            return DEFAULT_ENCODING
        for meta in content_type.split(b";")[1:]:
            if b"=" not in meta:
                continue
            key, value = meta.strip().split(b"=", 1)
            if key.strip() == b"charset":
                return value.strip().lower().decode()
        return DEFAULT_ENCODING
