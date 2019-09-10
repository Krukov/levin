import asyncio
from functools import partial

from .connection import Connection
from .middlewares import format_json
from .parsers.hyper import H2Manager
from .response import Response
from .router import HttpRouter
from .server import Server


async def not_found_handler(request):
    return Response(404, b"Not found")


class Application:
    def __init__(self, middlewares=(format_json(),), components=None):
        self.middlewares = middlewares
        self._components = components
        self.routes: HttpRouter = HttpRouter()

    async def handle(self, request):
        _handler = self.routes.resolve(request) or not_found_handler
        for middleware in self.middlewares:
            _handler = partial(middleware, handler=_handler)
        response: Response = await _handler(request)
        return response

    def _route(self, path, method):
        def _decorator(handler):
            self.routes.add(method, path, handler)
            return handler
        return _decorator

    def __getattr__(self, item):
        if item.upper() in ["GET", "POST", "PUT", "UPDATE", "DELETE"]:
            return partial(self._route, method=item.upper())
        return getattr(self, item)

    def run(self, host: str, port: int, app_loop=False, debug=False, connection_class=Connection, parser=H2Manager):
        asyncio.run(
            Server(connection_class, parser, app=self).run(host=host, port=port, debug=debug, app_loop=app_loop),
            debug=debug,
        )
