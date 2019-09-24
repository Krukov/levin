import asyncio

from levin.core.common import Request, Response
from levin.core.parsers.hyper import H2Manager


class Connection:
    __slots__ = ("_transport", "_parser", "_futures", "_loop", "_handle")

    def __init__(self, parser: H2Manager, handle, loop=None):
        self._loop = loop
        self._parser = parser
        self._handle = handle
        self._transport = None
        self._futures = []

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
                self._futures.append(asyncio.run_coroutine_threadsafe(self.handle_request(request), loop=self._loop))
        if close:
            self._transport.close()

    async def handle_request(self, request: Request):
        response = await self._handle(request)
        self.write_response(response, request)

    def write_response(self, response: Response, request: Request):
        for data in self._parser.handle_response(response, request):
            self.write(data)

    def eof_received(self):
        pass
