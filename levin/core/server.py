import asyncio
import threading
from concurrent.futures import CancelledError

from levin.core.connection import Connection
from levin.core.parsers.hyper import H2Manager

# https://ruslanspivak.com/lsbaws-part3/
# https://github.com/pgjones/hypercorn
# https://github.com/python-hyper/hyper-h2

# https://hub.docker.com/r/svagi/h2load
# https://www.protocols.ru/WP/rfc7540/
# http://plantuml.com/timing-diagram


class Server:
    """
    Implements connection management
    """

    def __init__(
        self,
        app,
        host: str = "127.0.0.1",
        port: int = 8000,
        connection_class=Connection,
        parser_class=H2Manager,
        loop=None,
    ):
        self._connection_class = connection_class
        self._parser_class = parser_class
        self._app = app
        self.host = host
        self.port = port
        self._loop = loop

    @property
    def loop(self):
        return self._loop or asyncio.get_running_loop()

    def handle_connection(self):
        return self._connection_class(self._parser_class(), loop=self.loop, handle=self._app.handle)

    def get_task(self, loop):
        return loop.create_server(self.handle_connection, self.host, self.port, reuse_address=True, reuse_port=False)

    async def start(self):
        await self._app.start()

    async def stop(self):
        await self._app.stop()


async def _manage(servers_async, servers, stop_event: asyncio.Event):
    try:
        await stop_event.wait()
    except CancelledError:
        pass
    for server in servers:
        await server.close()
    for server in servers_async:
        server.close()
        await server.wait_closed()


def run(*servers, loop=None, stop_event=asyncio.Event(), wait=True):
    if loop is None:
        loop = asyncio.new_event_loop()
    servers_async = [loop.create_task(server.get_task(loop)) for server in servers]
    if wait:
        manage_handler = loop.run_until_complete
    else:
        manage_handler = loop.create_task
    manage_handler(_manage(servers_async, servers, stop_event))


def create_loop_thread():
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    return loop
