import json
import os

from levin.core.common import Response
from levin.core.component import Component


def _default(obj):
    if isinstance(obj, bytes):
        return obj.decode()
    raise TypeError(f"Object of type {obj.__class__.__name__} " f"is not JSON serializable")


class JsonFormat(Component):
    name = "json_format"

    def __init__(
        self, dumps=json.dumps, default=_default, content_type=b"application/json", types_to_format=(dict, list, tuple)
    ):
        self._dumps = dumps
        self._default = default
        self._content_type = content_type
        self._types_to_format = types_to_format

    async def middleware(self, request, handler, call_next):
        response = await call_next(request, handler)
        if isinstance(response, self._types_to_format):
            data = self._dumps(response, default=self._default).encode()
            response = Response(
                status=request.get("status", 200), body=data, headers={b"content-type": self._content_type}
            )
        return response


class TextFormat(Component):
    name = "text_format"

    def __init__(self, content_type=b"text/html"):
        self._content_type = content_type

    async def middleware(self, request, handler, call_next):
        response = await call_next(request, handler)
        if isinstance(response, (str, bytes)):
            if isinstance(response, str):
                response = response.encode()
            response = Response(
                status=request.get("status", 200), body=response, headers={b"content-type": self._content_type}
            )
        return response


class TemplateFormat(Component):
    name = "templates"

    class Template:
        def __init__(self, path, context):
            self.path = path
            self.context = context

    def __init__(self, content_type=b"text/html", templates_dir: str = "./templates"):
        self._templates_dir = templates_dir

        self._content_type = content_type
        self._templates = {}

    def start(self, app):
        for root, dirs, files in os.walk(self._templates_dir):
            for _file in files:
                if not _file.endswith(".html"):
                    continue
                with open(os.path.join(root, _file)) as fd:
                    self._templates[_file] = fd.read()

    def render(self, path, context: dict, request=None):
        if path not in self._templates:
            raise Exception("Wrong template name")
        if request:
            context.update(request._scope)

        return self._templates[path].format(**{k: v.decode() if isinstance(v, bytes) else v for k, v in context.items()}).encode()

    async def middleware(self, request, handler, call_next):
        template = request.get("template")
        request.set("render", lambda r: lambda path, context: self.render(path, context, r))
        response = await call_next(request, handler)
        if isinstance(response, self.Template):
            response = Response(
                status=request.get("status", 200), body=self.render(response.path, response.context, request), headers={b"content-type": self._content_type}
            )
        if template and isinstance(response, dict):
            response = Response(
                status=request.get("status", 200),
                body=self.render(template, response, request),
                headers={b"content-type": self._content_type}
            )
        return response
