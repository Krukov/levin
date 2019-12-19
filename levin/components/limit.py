import asyncio

from levin.core.common import Request, Response
from levin.core.component import Component


class TimeLimit(Component):
    name = "handler_timeout"

    timeout: int = 10
    loop = None

    def start(self, app):
        self._loop = self.loop or asyncio.get_running_loop()  # pylint: disable:attribute-defined-outside-init

    @staticmethod
    async def _timeout_manager(value: int, task: asyncio.Task):
        await asyncio.sleep(value)
        if not task.done():
            task.cancel()

    async def middleware(self, request: Request, handler, call_next):

        task = asyncio.create_task(call_next(request, handler))  # task run in context copy
        timeout_task = self._loop.create_task(self._timeout_manager(self.timeout, task))
        try:
            return await task
        except asyncio.CancelledError:
            return Response(status=500, body=b"Timeout")
        finally:
            timeout_task.cancel()