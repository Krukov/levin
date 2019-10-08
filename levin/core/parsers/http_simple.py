from http import HTTPStatus

from ..common import ParseError, Request, Response

HTTP_STATUSES = {status.value: status.phrase.encode() for status in HTTPStatus}
HTTP_HEADERS = {b"content-type": b"Content-Type"}

_BLANK = b""


class Parser:
    def connect(self):
        pass

    def handle_request(self, data: bytes):

        method = path = protocol = _BLANK
        body = None
        headers = []
        for line in data.splitlines():
            if path == _BLANK:
                method, path, protocol = self._parse_first_line(line)
                continue
            if line == _BLANK:
                body = _BLANK
                continue
            if body is None:
                name, value = line.split(b":", 1)
                headers.append((name.strip().lower(), value.strip()))
            else:
                body += line
        if path and method and protocol:
            return b"", (Request(path=path, method=method, headers=tuple(headers), body=body),), False
        raise ParseError()

    @staticmethod
    def _parse_first_line(line: bytes) -> [bytes, bytes, bytes]:
        segments = line.split(b" ")
        if len(segments) != 3 or b"HTTP" not in segments[2]:
            raise Exception()
        method, path, version = segments
        return method.strip(), path.strip(), version.strip()

    @staticmethod
    def handle_response(response: Response, request: Request):
        headers = response.headers
        if response.body:
            headers[b"Content-Length"] = str(len(response.body)).encode()
        headers = b"\r\n".join([b": ".join([HTTP_HEADERS.get(k, k.capitalize()), v]) for k, v in headers.items()])
        yield b"HTTP/1.1 " + str(response.status).encode() + b" " + HTTP_STATUSES.get(response.status) + b"\r\n"
        yield headers
        if response.body:
            yield b"\r\n\r\n" + response.body
        yield b"\r\n"
