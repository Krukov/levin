from typing import Mapping, Tuple

empty = object()


class ParseError(Exception):
    pass


class HeadersProxy:
    __slots__ = ("__target",)

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
    return HeadersProxy({name: b"; ".join(value) for name, value in _headers.items()})


class Request:
    __slots__ = ("path", "method", "body", "headers", "stream", "protocol", "_scope")

    def __init__(
        self,
        path: bytes = b"/",
        method: bytes = b"GET",
        body: bytes = b"",
        headers: Tuple = (),
        protocol: bytes = b"",
        stream: int = 0,
    ):
        self.path = path
        self.method = method
        self.body = body
        self.headers = create_headers_map(headers)
        self.stream = stream
        self.protocol = protocol
        self._scope = {}

    def __getattr__(self, item):
        if item in Request.__slots__:
            # it's happened on unpickle request (multiprocessing)
            return None
        attr = self.get(item, default=empty)
        if attr is empty:
            raise AttributeError(f"Request has no attr {item} in scope")
        return attr

    def get(self, item, default=None):
        attr = self._scope.get(item, default)
        if callable(attr) and attr != default:
            attr = attr(self)
            self._scope[item] = attr
        return attr

    def set(self, key, value):
        if key not in self._scope:
            self._scope[key] = value


class Response:
    __slots__ = ("status", "body", "headers")

    def __init__(self, status: int, body: bytes, headers=None):
        self.status = status
        self.body = body
        self.headers = headers or {}


class PseudoConnection:
    __slots__ = ("peername", "_close", "requests")
