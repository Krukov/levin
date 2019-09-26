import asyncio
import traceback
from functools import partial

from levin.core.common import Request, Response
from levin.core.parsers.hyper import H2Manager

response_500 = Response(status=500, body=b"Sorry")


class Connection:
    __slots__ = ("_transport", "_parser", "_futures", "_loop", "_handler")

    def __init__(self, parser: H2Manager, handler, loop=None):
        self._loop = loop
        self._parser = parser
        self._handler = handler
        self._transport = None
        self._futures = []

    def _done_callback(self, future, request=None):
        if future.cancelled():
            self.write_response(response_500, request)
        elif future.exception():
            self.write_response(response_500, request)
            traceback.print_exception(None, future.exception(), future.exception().__traceback__)
        self._futures.remove(future)

    def write(self, data):
        self._transport.write(data)

    def connection_made(self, transport: asyncio.Transport):
        self._transport = transport
        self.write(self._parser.connect())

    def connection_lost(self, exc):
        for future in self._futures:
            future.cancel()

    def data_received(self, data: bytes):
        data, requests, close = self._parser.handle_request(data)
        if data:
            self.write(data)
        if requests:
            for request in requests:
                future = asyncio.run_coroutine_threadsafe(self.handle_request(request), loop=self._loop)
                self._futures.append(future)
                future.add_done_callback(partial(self._done_callback, request=request))
        if close:
            self._transport.close()

    async def handle_request(self, request: Request):
        response = await self._handler(request)
        self.write_response(response, request)

    def write_response(self, response: Response, request: Request):
        for data in self._parser.handle_response(response, request):
            self.write(data)

    def eof_received(self):
        pass
