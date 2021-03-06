import asyncio
import json
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse
import sys

from levin.core.common import Request, Response
from levin.core.component import Component
from better_exceptions import excepthook, ExceptionFormatter, to_byte

DEFAULT_ENCODING = "iso-8859-1"
CONTENT_TYPE_HEADER = b"content-type"

formatter = ExceptionFormatter(colored=False, pipe_char='|', cap_char='->')


def _default_on_error(request, exception):
    excepthook(exception.__class__, exception, sys.exc_info()[2])
    return Response(status=500, body=to_byte(formatter.format_exception(exception.__class__, exception, sys.exc_info()[2])))


class ErrorHandle(Component):
    name = "error_handle"
    on_error = staticmethod(_default_on_error)

    async def middleware(self, request: Request, handler, call_next):
        try:
            return await call_next(request, handler)
        except Exception as exc:  # pylint: disable=broad-except
            response = self.on_error(request, exc)
            if asyncio.iscoroutine(response):
                response = await response
            return response


class PatchRequest(Component):
    name = "patch_request"

    json_loads = staticmethod(json.loads)
    json_content_type = b"application/json"
    parse_url = staticmethod(urlparse)
    parse_query_params = staticmethod(parse_qs)

    def middleware(self, request: Request, handler, call_next):
        request.set("data", self._data, lazy=True)
        request.set("path", self._path, lazy=True)
        request.set("query_params", self._query_params, lazy=True)
        request.set("json", self._json, lazy=True)
        request.set("content_type", self._content_type, lazy=True)
        request.set("encoding", self._encoding, lazy=True)
        return call_next(request, handler)

    def _json(self, request: Request) -> Optional[dict]:
        if request.content_type == self.json_content_type:
            return self.json_loads(request.body.decode(request.encoding))
        return None

    def _data(self, request) -> dict:
        pass  # todo: parse multipart form data

    def _parse_url(self, request):
        parsed_url = self.parse_url(request.raw_path)
        request.set("path", parsed_url.path)
        query_params = self.parse_query_params(parsed_url.query)
        request.set("query_params", query_params)
        return parsed_url.path, query_params

    def _path(self, request: Request) -> bytes:
        if b"?" not in request.raw_path:
            return request.raw_path
        return self._parse_url(request)[0]

    def _query_params(self, request: Request) -> Dict[str, str]:
        if b"?" not in request.raw_path:
            return {}
        return self._parse_url(request)[1]

    @staticmethod
    def _content_type(request: Request) -> Optional[bytes]:
        content_type = request.headers.get(CONTENT_TYPE_HEADER)
        if content_type:
            return content_type.split(b";", 1)[0]
        return None

    @staticmethod
    def _encoding(request: Request) -> str:
        content_type = request.headers.get(CONTENT_TYPE_HEADER)
        if not content_type or b";" not in content_type:
            return DEFAULT_ENCODING
        for meta in content_type.split(b";")[1:]:
            if b"=" not in meta or meta.strip().split(b"=", 1)[0].strip() != b"charset":
                continue
            return meta.strip().split(b"=", 1)[0].strip().lower().decode()
        return DEFAULT_ENCODING


