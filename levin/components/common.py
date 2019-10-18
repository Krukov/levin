import asyncio
import json
import traceback

from levin.core.common import Request, Response
from levin.core.component import Component

DEFAULT_ENCODING = "iso-8859-1"
CONTENT_TYPE_HEADER = b"content-type"


def _default_on_error(request, exception):
    traceback.print_exception(None, exception, exception.__traceback__)
    return Response(status=500, body=traceback.format_exc().encode())


def handle_error(on_error=_default_on_error):
    async def middleware(request: Request, handler, call_next):
        try:
            return await call_next(request, handler)
        except Exception as exc:
            response = on_error(request, exc)
            if asyncio.iscoroutine(response):
                response = await response
            return response

    return middleware


class TimeLimit(Component):
    name = "handler_timeout"

    timeout: int = 10
    loop = None

    def start(self, app):
        self._loop = self.loop or asyncio.get_running_loop()

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


class PatchRequest(Component):
    name = "patch_request"

    json_loads = staticmethod(json.loads)
    json_content_type = b"application/json"

    async def middleware(self, request: Request, handler, call_next):
        request.set("data", self.data)
        request.set("json", self.json)
        request.set("content_type", self.content_type)
        request.set("encoding", self.encoding)
        return await call_next(request, handler)

    def json(self, request) -> dict:
        if request.content_type == self.json_content_type:
            return self.json_loads(request.body.decode(request.encoding))

    def data(self, request) -> dict:
        pass  # todo: parse multipart form data

    @staticmethod
    def content_type(request) -> bytes:
        content_type = request.headers.get(CONTENT_TYPE_HEADER)
        if content_type:
            return content_type.split(b";", 1)[0]

    @staticmethod
    def encoding(request) -> str:
        content_type = request.headers.get(CONTENT_TYPE_HEADER)
        if not content_type or b";" not in content_type:
            return DEFAULT_ENCODING
        for meta in content_type.split(b";")[1:]:
            if b"=" not in meta:
                continue
            key, value = meta.strip().split(b"=", 1)
            if key.strip() == b"charset":
                return value.strip().lower().decode()
        return DEFAULT_ENCODING
