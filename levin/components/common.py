import asyncio
import json
import traceback

from levin.core.common import Request, Response
from levin.core.component import Component

DEFAULT_ENCODING = "iso-8859-1"
CONTENT_TYPE_HEADER = b"content-type"
JSON_CONTENT = b"application/json"


def _default_on_error(request, exception):
    return Response(status=500, body=traceback.format_exc().encode())


def handle_error(on_error=_default_on_error):
    async def middleware(request: Request, handler):
        try:
            return await handler(request)
        except Exception as exc:
            response = on_error(request, exc)
            if asyncio.iscoroutine(response):
                response = await response
            return response

    return middleware


class TimeLimit(Component):
    def __init__(self, timeout=60, loop=None):
        self.__timeout = timeout
        self.__loop = loop or asyncio.get_running_loop()

    @staticmethod
    async def _timeout_manager(value: int, task: asyncio.Task):
        await asyncio.sleep(value)
        if not task.done():
            task.set_result(Response(status=500, body=traceback.format_list(task.get_stack()).encode()))

    async def middleware(self, request: Request, handler):
        task = asyncio.create_task(handler(request))  # task run in context copy
        timeout_task = self.__loop.create_task(self._timeout_manager(self.__timeout, task))
        try:
            return await task
        finally:
            timeout_task.cancel()


class PatchRequest(Component):
    def __init__(self, json_loads=json.loads):
        self._json_loads = json_loads

    async def middleware(self, request: Request, handler):
        request.set("json", self.data)
        request.set("json", self.json)
        request.set("content_type", self.content_type)
        request.set("encoding", self.encoding)
        return await handler(request)

    def json(self, request):
        if request.content_type == JSON_CONTENT:
            return self._json_loads(request.body.decode(request.encoding))

    def data(self, request):
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
