import asyncio
import re
from typing import Awaitable, Callable, Dict, List, Type, Union


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


class ConnectionManagerProtocol:
    _connections: List["Connection"]

    def on_connection_open(self, connection: "Connection"):
        pass

    def on_request_start(self, connection: "Connection", request: Request):
        pass

    def on_request_finish(self, connection: "Connection", request: Request):
        pass

    def on_connection_close(self, connection: "Connection"):
        pass


ConnectionManager = Type[ConnectionManagerProtocol]


class ConnectionProtocol(asyncio.Protocol):
    manager: ConnectionManager
    parser: Parser
    handler: Callable

    def __init__(self, manager: type, parser: Parser, handler: Handler):
        pass


Connection = Type[ConnectionProtocol]

CompiledRe = type(re.compile(""))
Pattern = Union[bytes, str, CompiledRe]
