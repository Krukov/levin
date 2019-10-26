import asyncio
import traceback
from functools import partial

from .common import ParseError, Request, Response

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
        if requests:
            for request in requests:
                future = asyncio.run_coroutine_threadsafe(self.handle_request(request), loop=self._loop)
                self._futures.append(future)
                future.add_done_callback(partial(self._done_callback, request=request))
        if close:
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

    async def handle_request(self, request: Request):
        response = await self._handler(request)
        self.write_response(response, request)

    def write_response(self, response: Response, request: Request):
        for data in self._parser.handle_response(response, request):
            self.write(data)

    def eof_received(self):
        pass

    def close(self):
        self._transport.close()
        for future in self._futures:
            future.set_exception(CloseException())
