import asyncio

import traceback
from functools import partial

from levin.parsers.hyper import H2Manager
from levin.request import Request
from levin.response import Response

response_500 = Response(status=500, body=b"Sorry")


class TimeOut(Exception):
    pass


class Connection:
    __slots__ = ("_transport", "_manager", "_futures", "_loop", "_app", "_main_loop")

    def __init__(self, manager: H2Manager, app, loop=None, main_loop=None):
        self._loop = loop
        self._main_loop = main_loop
        self._manager = manager
        self._app = app
        self._transport = None
        self._futures = []

    def write(self, data):
        self._transport.write(data)

    def connection_made(self, transport: asyncio.Transport):
        self._transport = transport
        self.write(self._manager.connect())

    def connection_lost(self, exc):
        for future in self._futures:
            future.cancel()

    def _handler_callback(self, task: asyncio.Task, stream: int = 0, timeout_future=None):
        if task.cancelled():
            self.write_response(response_500, stream)
            return
        if task.exception():
            self.write_response(response_500, stream)
            traceback.print_exception(None, task.exception(), task.exception().__traceback__)
        timeout_future.cancel()
    
    async def _timeout_handler(self, future: asyncio.Future):
        await asyncio.sleep(5)
        if not future.done():
            future.cancel()

    def data_received(self, data: bytes):
        asyncio.run_coroutine_threadsafe(self._data_received(data), loop=self._loop)

    async def _data_received(self, data: bytes):
        data, requests, close = self._manager.handle_request(data)
        if data:
            self.write(data)
        if requests:
            for request in requests:
                future = asyncio.run_coroutine_threadsafe(self.handle_request(request), loop=self._loop)
                timeout_future = asyncio.ensure_future(self._timeout_handler(future), loop=self._main_loop)
                future.add_done_callback(partial(self._handler_callback, stream=request.stream, timeout_future=timeout_future))
        if close:
            self._transport.close()

    async def handle_request(self, request: Request):
        handler = self._app.handle(request)
        self.write_response(await handler, request.stream)

    def write_response(self, response: Response, stream):
        response.headers[b"content-length"] = str(len(response.body)).encode()
        for data in self._manager.handle_response(response, stream=stream):
            self.write(data)

    def eof_received(self):
        pass
