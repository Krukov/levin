import json
import os
import string
from typing import Callable, Tuple, Type

from .cli import command
from levin.core.common import Response
from levin.core.component import Component


def _default(obj):
    if isinstance(obj, bytes):
        return obj.decode()
    raise TypeError(f"Object of type {obj.__class__.__name__} " f"is not JSON serializable")


class JsonFormat(Component):
    name = "json_format"

    json_dumps = staticmethod(json.dumps)
    default: Callable = staticmethod(_default)
    content_type: bytes = b"application/json"
    types_to_format: Tuple[Type] = (dict, list, tuple)

    async def middleware(self, request, handler, call_next):
        response = await call_next(request, handler)
        if isinstance(response, self.types_to_format):
            if self.default:
                data = self.json_dumps(response, default=self.default)
            else:
                data = self.json_dumps(response)
            response = Response(
                status=request.get("status", 200), body=data.encode(), headers={b"content-type": self.content_type}
            )
        return response


class TextFormat(Component):
    name = "text_format"

    content_type: bytes = b"text/html"

    async def middleware(self, request, handler, call_next):
        response = await call_next(request, handler)
        if isinstance(response, (str, bytes)):
            if isinstance(response, str):
                response = response.encode()
            response = Response(
                status=request.get("status", 200), body=response, headers={b"content-type": self.content_type}
            )
        return response


class TemplateFormat(Component):
    name = "templates"

    templates_dirs: Tuple[str] = ("./templates",)
    templates_formats: Tuple[str] = (".html",)
    content_type: bytes = b"text/html"

    class Template:
        def __init__(self, path, context):
            self.path = path
            self.context = context

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._templates = {}

    def init(self, app):
        for _dir in self.templates_dirs:
            for root, _, files in os.walk(_dir):
                self._check_and_save(files, root)

    def _check_and_save(self, files, root: str):
        for file_ in files:
            if not file_.endswith(self.templates_formats):
                continue
            with open(os.path.join(root, file_)) as open_file:
                self._templates[(root, file_)] = open_file.read()

    def _get_template(self, name):
        for _, file_ in self._templates:
            if file_ == name:
                return self._templates[(_, file_)]
        return None

    def render(self, path, context: dict, request=None):
        template = self._get_template(path)
        if not template:
            raise Exception("Wrong template name")
        if request:
            context.update(request._scope)  # pylint: disable=protected-access

        return (
            string.Template(template=template)
            .safe_substitute(**{k: v.decode() if isinstance(v, bytes) else v for k, v in context.items()})
            .encode()
        )

    async def middleware(self, request, handler, call_next):
        template = request.get("template")
        response = await call_next(request, handler)
        if isinstance(response, self.Template):
            response = Response(
                status=request.get("status", 200),
                body=self.render(response.path, response.context, request),
                headers={b"content-type": self.content_type},
            )
        if template and isinstance(response, dict):
            response = Response(
                status=request.get("status", 200),
                body=self.render(template, response, request),
                headers={b"content-type": self.content_type},
            )
        return response

    @command
    def list(self):
        return self._templates.keys()
