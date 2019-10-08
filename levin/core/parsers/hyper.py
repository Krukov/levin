from typing import Dict, List, Optional, Tuple

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import ConnectionTerminated, DataReceived, RequestReceived, StreamEnded
from h2.exceptions import ProtocolError, StreamClosedError

from ..common import ParseError, Request, Response
from .http_simple import Parser as Http1Parser


def _get_request_from_event(event):
    headers = []
    method = b"GET"
    path = b"/"
    for name, value in event.headers:
        if name.startswith(":"):
            if name == ":method":
                method = value.encode()
            elif name == ":path":
                path = value.encode()
            continue
        headers.append((name.encode(), value.encode()))
    return Request(method=method, path=path, headers=tuple(headers), stream=event.stream_id)


class Parser:
    config = H2Configuration(client_side=False, header_encoding="utf-8")

    __slots__ = ("conn", "_streams")

    def __init__(self):
        self.conn = H2Connection(config=self.config)
        self._streams: Dict[int, Request] = {}

    def connect(self):
        self.conn.initiate_connection()

    def handle_request(self, data: bytes) -> Tuple[Optional[bytes], Optional[List[Request]], bool]:
        to_send_data = None
        requests = []
        close = False
        try:
            events = self.conn.receive_data(data)
        except ProtocolError as exc:
            # try parse http1.1 and send change connection
            request, to_send_data = self.handle_http1_to_http2(data)
            events = []
            if not to_send_data:
                raise ParseError() from exc
            self.conn.clear_outbound_data_buffer()  # clean init connection
            self.conn.initiate_upgrade_connection(settings_header=request.headers[b"http2-settings"])
            to_send_data += b"\r\n" + self.conn.data_to_send()
            requests.append(request)
        to_send_data = to_send_data if to_send_data is not None else self.conn.data_to_send()

        for event in events:
            if isinstance(event, RequestReceived):
                self._streams[event.stream_id] = _get_request_from_event(event)
            elif isinstance(event, DataReceived):
                if event.stream_id in self._streams:
                    self._streams[event.stream_id].body += event.data
            elif isinstance(event, StreamEnded):
                requests.append(self._streams.get(event.stream_id))
            elif isinstance(event, ConnectionTerminated):
                # Stop all requests
                close = True

        return to_send_data, requests, close

    def handle_http1_to_http2(self, data: bytes) -> Tuple[Optional[Request], bytes]:
        if b"HTTP" not in data:
            return None, b""
        parser = Http1Parser()
        data, requests, close = parser.handle_request(data)
        if len(requests) == 1:
            request = requests[0]
            settings = request.headers.get(b"http2-settings")
            if request.headers.get(b"upgrade") != b"h2c" or not settings:
                return request, b""
            response = Response(101, b"", headers={b"Connection": b"Upgrade", b"Upgrade": b"h2c"})
            request.stream = 1
            return request, b"".join(parser.handle_response(response, requests))
        return None, b""

    def handle_response(self, response: Response, request: Request):
        response.headers[b"content-length"] = str(len(response.body)).encode()
        response_headers = ((":status", str(response.status)),) + tuple(response.headers.items())
        self.conn.send_headers(request.stream, response_headers)
        data = response.body
        while True:
            if self.conn.local_flow_control_window(request.stream) < 1:
                return

            chunk_size = min(
                self.conn.local_flow_control_window(request.stream), len(data), self.conn.max_outbound_frame_size
            )
            try:
                self.conn.send_data(request.stream, data[:chunk_size], end_stream=(chunk_size >= len(data)))
            except (StreamClosedError, ProtocolError):
                # The stream got closed and we didn't get told. We're done here.
                break

            yield self.conn.data_to_send()
            data = data[chunk_size:]
            if not data:
                return
