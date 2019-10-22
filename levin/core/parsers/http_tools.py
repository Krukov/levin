from httptools import HttpParserInvalidMethodError, HttpRequestParser

from ..common import ParseError, Request
from .http_simple import Parser as SimpleParser


class _PRequest:
    """
    Object to store parsing result
    """

    __slots__ = ("headers", "path", "body", "ready")

    def __init__(self):
        self.headers = []
        self.path = None
        self.body = b""
        self.ready = False

    def on_url(self, url: bytes):
        self.path = url

    def on_header(self, name: bytes, value: bytes):
        self.headers.append((name.lower(), value))

    def on_body(self, body: bytes):
        self.body = body

    def on_message_complete(self):
        self.ready = True


class Parser(SimpleParser):
    def handle_request(self, data: bytes):
        request = _PRequest()
        parser = HttpRequestParser(request)
        try:
            parser.feed_data(data)
        except HttpParserInvalidMethodError:
            raise ParseError()
        if request.ready:
            return (
                b"",
                (
                    Request(
                        path=request.path,
                        method=parser.get_method(),
                        headers=tuple(request.headers),
                        body=request.body,
                        protocol=b"HTTP/" + parser.get_http_version().encode(),
                    ),
                ),
                False,
            )
        raise ParseError()
