import asyncio

from levin.core.connection import Connection
from levin.core.parsers.http_simple import Parser as Http1Parser
from levin.core.parsers.http_tools import Parser as Http1ParserHttpTools
from levin.core.parsers.hyper import Parser as Http2Parser

# https://medium.com/@pgjones/an-asyncio-socket-tutorial-5e6f3308b8b0
# https://hpbn.co/http2/
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
        parsers_class=(Http2Parser, Http1ParserHttpTools),
        loop=None,
    ):
        self._connection_class = connection_class
        self._parsers_class = parsers_class
        self._app = app
        self.host = host
        self.port = port
        self._loop = loop

    @property
    def loop(self):
        return self._loop or asyncio.get_running_loop()

    def handle_connection(self):
        return self._connection_class(
            [parser() for parser in self._parsers_class], loop=self.loop, handler=self._app.handler
        )

    async def get_task(self, loop, stop_event):
        try:
            return await loop.create_server(
                self.handle_connection, self.host, self.port, reuse_address=True, reuse_port=False
            )
        except Exception:
            stop_event.set()

    async def start(self):
        await self._app.start()

    async def stop(self):
        await self._app.stop()


async def _manage(servers_async, servers, stop_event: asyncio.Event):
    try:
        await stop_event.wait()
    except:
        pass
    for server in servers:
        await server.stop()
    for server in servers_async:
        server_result = server.result()
        if isinstance(server_result, asyncio.AbstractServer):
            server_result.close()
            await server_result.wait_closed()
        if not server.done():
            server.cancel()


def run(*servers, loop=None, stop_event=None, wait=True):
    if loop is None:
        loop = asyncio.new_event_loop()
    if stop_event is None:
        stop_event = asyncio.Event(loop=loop)
    for server in servers:
        loop.run_until_complete(server.start())
    servers_async = [loop.create_task(server.get_task(loop, stop_event)) for server in servers]
    if wait:
        manage_handler = loop.run_until_complete
    else:
        manage_handler = loop.create_task
    try:
        manage_handler(_manage(servers_async, servers, stop_event))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            stop_event.set()
            asyncio.runners._cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()


def run_app(app, host: str = "0.0.0.0", port: int = 8000):
    return run(Server(app, host=host, port=port))


def run_apps(*args):
    servers = []
    app, port = None, None
    for n, arg in enumerate(args):
        if isinstance(arg, (list, tuple)):
            app, port = arg
        elif not n % 2:
            app = arg
            port = None
        else:
            port = arg
        servers.append(Server(app, host="0.0.0.0", port=port))
    run(*servers)
