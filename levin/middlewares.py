import json

from .response import Response


def format_json(dumps=json.dumps):
    async def middleware(request, handler):
        response = await handler(request)
        if not isinstance(response, Response):
            data = dumps(response).encode()
            response = Response(status=200, body=data, headers={b"content-type": b"application/json"})
        return response

    return middleware
