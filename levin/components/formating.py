import json

from levin.core.common import Response
from levin.core.component import Component


def _default(obj):
    if isinstance(obj, bytes):
        return obj.decode()
    raise TypeError(f"Object of type {obj.__class__.__name__} " f"is not JSON serializable")


class JsonFormat(Component):
    def __init__(self, dumps=json.dumps, default=_default, content_type=b"application/json"):
        self._dumps = dumps
        self._default = default
        self._content_type = content_type

    async def middleware(self, request, handler):
        response = await handler(request)
        if not isinstance(response, Response):
            data = self._dumps(response, default=self._default).encode()
            response = Response(
                status=request.get("status", 200), body=data, headers={b"content-type": self._content_type}
            )
        return response


class TextFormat(Component):
    def __init__(self, content_type=b"application/json"):
        self._content_type = content_type

    async def middleware(self, request, handler):
        response = await handler(request)
        if isinstance(response, (str, bytes)):
            if isinstance(response, str):
                response = response.encode()
            response = Response(
                status=request.get("status", 200), body=response, headers={b"content-type": self._content_type}
            )
        return response
