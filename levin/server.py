import asyncio
import threading
import time

# https://ruslanspivak.com/lsbaws-part3/
# https://github.com/pgjones/hypercorn
# https://github.com/python-hyper/hyper-h2

# https://hub.docker.com/r/svagi/h2load
# https://www.protocols.ru/WP/rfc7540/
# http://plantuml.com/timing-diagram


class Server:
    """
    Server implement connection management and requests managment
    """

    def __init__(self, connection_class, parser, app):
        self._connection_class = connection_class
        self._parser = parser
        self._app_loop = None
        self._main_loop = None
        self._app = app

    def __call__(self):
        return self._connection_class(self._parser(), loop=self._get_app_loop(), app=self._app, main_loop=self._main_loop)

    def _get_app_loop(self):
        return self._app_loop or self._main_loop

    async def run(self, host: str = "127.0.0.1", port: int = 8000, debug: bool = False, app_loop=True, sleep=1):
        loop = asyncio.get_running_loop()
        if app_loop:
            self._app_loop = create_loop_thread()
        self._main_loop = loop
        self._get_app_loop().set_debug(debug)
        server = await loop.create_server(self, host, port, reuse_address=True, reuse_port=True)
        print("Serving on {}, {}".format(server.sockets[0].getsockname(), self._app_loop))
        while True:
            start = time.monotonic()
            await asyncio.sleep(sleep)
            diff = time.monotonic() - start - sleep
            if diff > sleep:
                print(f"Loop under problem (diff: {diff}, tasks: {len(asyncio.all_tasks(self._get_app_loop()))})")


def create_loop_thread():
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    return loop
