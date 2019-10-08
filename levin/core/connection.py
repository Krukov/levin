import asyncio
import traceback
from functools import partial

from .common import ParseError, Request, Response

response_500 = Response(status=500, body=b"Sorry")


class Connection:
    __slots__ = ("_transport", "_parsers", "_parser", "_futures", "_loop", "_handler")

    def __init__(self, parsers, handler, loop=None):
        self._loop = loop
        self._parsers = parsers
        self._parser = None
        self._handler = handler
        self._transport = None
        self._futures = []

    def _done_callback(self, future: asyncio.Future, request=None):
        if future.cancelled() and self._transport and not self._transport.is_closing():
            self.write_response(response_500, request)
        else:
            try:
                exception = future.exception()
            except (asyncio.CancelledError, asyncio.InvalidStateError) as exc:
                exception = exc
            if exception:
                traceback.print_exception(None, exception, exception.__traceback__)
                self.write_response(response_500, request)
        self._futures.remove(future)

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
        requests = ()
        close = True
        _data = None
        for parser in self._parsers:
            try:
                _data, requests, close = parser.handle_request(data)
            except ParseError as exc:
                print(exc)
                continue
            else:
                self._parser = parser
                break

        if _data:
            self.write(_data)
        if requests:
            for request in requests:
                future = asyncio.run_coroutine_threadsafe(self.handle_request(request), loop=self._loop)
                self._futures.append(future)
                future.add_done_callback(partial(self._done_callback, request=request))
        if close:
            self.close()

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
            future.cancel()
