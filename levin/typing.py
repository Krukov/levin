import re
from typing import Awaitable, Callable, Dict, Iterator, List, Tuple, Type, Union


class ASGI2Protocol:
    def __init__(self, scope: dict) -> None:
        ...

    async def __call__(self, receive: Callable, send: Callable) -> None:
        ...


ASGI2Framework = Type[ASGI2Protocol]
ASGI3Framework = Callable[[dict, Callable, Callable], Awaitable[None]]
ASGIFramework = Union[ASGI2Framework, ASGI3Framework]


class RequestProtocol:
    method: bytes
    path: bytes
    body: str
    content_type: bytes
    encoding: str
    protocol: bytes

    def __init__(self, path: bytes, method: bytes, body: bytes, headers: tuple = ()):
        pass

    def __getitem__(self, item):
        pass

    def __setitem__(self, key, value):
        pass


Request = Type[RequestProtocol]


class ResponseProtocol:
    status: int
    body: str
    headers: Dict[bytes, bytes]


Response = Type[ResponseProtocol]
Handler = Callable[[Request], Response]
Parser = Callable[[bytes], Request]

CompiledRe = type(re.compile(""))
Pattern = Union[bytes, str, CompiledRe]


class ParserProtocol:
    def connect(self) -> bytes:
        ...

    def handle_request(self, data: bytes) -> Tuple[bytes, List[Request], bool]:
        ...

    def handle_response(self, response, request) -> Iterator[bytes]:
        ...
