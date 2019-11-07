import asyncio
import traceback
from functools import partial

from .common import ParseError, Request, Response, Push

response_500 = Response(status=500, body=b"Sorry")  # pylint: disable=invalid-name


class CloseException(Exception):
    pass


class Connection:
    __slots__ = ("_transport", "_parsers", "_parser", "_futures", "_loop", "_handler")

    def __init__(self, parsers, handler, loop=None):
        self._loop = loop
        self._parsers = parsers
        self._parser = None
        self._handler = handler
        self._transport = None
        self._futures = []

    @staticmethod
    def _get_future_exception(future):
        try:
            return future.exception()
        except asyncio.InvalidStateError as exc:
            return exc
        except asyncio.CancelledError:  # connection lost
            return None

    @property
    def is_ssl(self) -> bool:
        return bool(self._transport.get_extra_info("sslcontext"))

    @property
    def scheme(self) -> bytes:
        if self.is_ssl:
            return b"https"
        return b"http"

    def _done_callback(self, future: asyncio.Future, request=None):
        try:
            if future.cancelled():
                self._write_500(request)
                return
            exception = self._get_future_exception(future)
            if exception:
                traceback.print_exception(None, exception, exception.__traceback__)
                self._write_500(request)
        finally:
            self._futures.remove(future)

    def _close_callback(self, future):
        self.close()

    def _write_500(self, request):
        if self._transport and not self._transport.is_closing():
            self.write_response(response_500, request)

    def write(self, data):
        self._transport.write(data)

    def connection_made(self, transport: asyncio.Transport):
        self._transport = transport
        for parser in self._parsers:
            parser.connect()

    def connection_lost(self, exc):
        for future in self._futures:
            future.cancel()

    def data_received(self, data: bytes):
        _data, requests, close = self._parse(data)
        if _data:
            self.write(_data)
        future = None
        if requests:
            for request in requests:
                future = asyncio.run_coroutine_threadsafe(self.handle_request(request), loop=self._loop)
                self._futures.append(future)
                future.add_done_callback(partial(self._done_callback, request=request))
        if close:
            if future:
                future.add_done_callback(self._close_callback)
            else:
                self.close()

    def _parse(self, data):
        if self._parser:
            return self._parser.handle_request(data)
        for parser in self._parsers:
            try:
                parsed = parser.handle_request(data)
            except ParseError:
                continue
            else:
                self._parser = parser
                return parsed

    def _get_transport_info(self, request):
        def info():
            return self._transport.get_extra_info('peername'), self._transport.get_extra_info('sockname')
        return info

    async def handle_request(self, request: Request):
        request.set('get_transport_info', self._get_transport_info, lazy=True)
        response: Response = await self._handler(request)
        self.write_response(response, request)
        if response.pushes and self._parser and getattr(self._parser, "push_support", False):
            await asyncio.gather(*[self.handle_push(push, request) for push in response.pushes])

    async def handle_push(self, push: Push, request):
        _request = Request(path=push.path, method=push.method, protocol=request.protocol, headers=request.headers.items(), stream=request.stream, scheme=self.scheme)
        _request.set('get_transport_info', self._get_transport_info, lazy=True)
        response: Response = await self._handler(_request)
        response.push = True
        self.write_response(response, _request)

    def write_response(self, response: Response, request: Request):
        for data in self._parser.handle_response(response, request):
            self.write(data)

    def eof_received(self):
        pass

    def close(self):
        self._transport.close()
        for future in self._futures:
            future.set_exception(CloseException())
