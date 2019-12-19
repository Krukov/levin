import asyncio
import ssl as ssl_lib

from typing import Optional, Tuple

from levin.core.connection import Connection
from levin.core.parsers.http_simple import Parser as Http1Parser
from levin.core.parsers.http_tools import Parser as Http1ParserHttpTools
from levin.core.parsers.hyper import Parser as Http2Parser

# https://medium.com/@pgjones/an-asyncio-socket-tutorial-5e6f3308b8b0
# https://hpbn.co/http2/
# https://ruslanspivak.com/lsbaws-part3/
# https://github.com/pgjones/hypercorn
# https://github.com/python-hyper/hyper-h2
# https://medium.com/python-pandemonium/how-to-serve-http-2-using-python-5e5bbd1e7ff1

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
        parsers_class=(Http2Parser, Http1Parser, Http1ParserHttpTools),
        ssl: Optional[Tuple[str, str]] = None,
        loop=None,
    ):  # pylint: disable=too-many-arguments
        self._connection_class = connection_class
        self._parsers_class = parsers_class
        self._app = app
        self.host = host
        self.port = port
        self._loop = loop
        self.ssl_context = None
        if ssl:
            self.ssl_context = self.create_ssl_context(*ssl)

    @staticmethod
    def create_ssl_context(certfile, keyfile):
        ssl_context = ssl_lib.create_default_context(ssl_lib.Purpose.CLIENT_AUTH)
        ssl_context.options |= (
                ssl_lib.OP_NO_TLSv1 | ssl_lib.OP_NO_TLSv1_1 | ssl_lib.OP_NO_COMPRESSION
        )
        ssl_context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        ssl_context.set_alpn_protocols(["h2"])
        return ssl_context

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
                self.handle_connection, self.host, self.port, reuse_address=True, reuse_port=False, ssl=self.ssl_context)
        except Exception:  # pylint: disable=broad-except
            stop_event.set()

    async def start(self):
        await self._app.start()

    async def stop(self):
        await self._app.stop()


async def _manage(servers_async, servers, stop_event: asyncio.Event):
    try:
        await stop_event.wait()
    except Exception:  # pylint: disable=broad-except
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
    stop_event = stop_event or asyncio.Event(loop=loop)
    for server in servers:
        loop.run_until_complete(server.start())

    manage_handler = loop.create_task
    if wait:
        manage_handler = loop.run_until_complete
    try:
        manage_handler(
            _manage([loop.create_task(server.get_task(loop, stop_event)) for server in servers], servers, stop_event)
        )
    except:
        pass
    finally:
        _stop(stop_event, loop)


def _stop(stop_event, loop):
    try:
        stop_event.set()
        asyncio.runners._cancel_all_tasks(loop)  # pylint: disable=protected-access
        loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        loop.close()


def run_app(app, host: str = "0.0.0.0", port: int = 8000, ssl=None):
    return run(Server(app, host=host, port=port, ssl=ssl))


def run_apps(*args):
    servers = []
    app, port = None, None
    for arg_index, arg in enumerate(args):
        if isinstance(arg, (list, tuple)):
            app, port = arg
        elif not arg_index % 2:
            app = arg
            port = None
        else:
            port = arg
        servers.append(Server(app, host="0.0.0.0", port=port))
    run(*servers)

