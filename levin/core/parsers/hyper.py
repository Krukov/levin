from typing import Dict, List, Optional, Tuple

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import ConnectionTerminated, DataReceived, RequestReceived, StreamEnded
from h2.exceptions import ProtocolError, StreamClosedError

from levin.core.common import Request, Response


def _get_request_from_event(event):
    headers = []
    method = b"GET"
    path = b"/"
    for name, value in event.headers:
        if name.startswith(":"):
            if name == ":method":
                method = value.encode()
            if name == ":path":
                path = value.encode()
            continue
        headers.append((name.encode(), value.encode()))
    return Request(method=method, path=path, headers=tuple(headers), stream=event.stream_id)


class H2Manager:
    config = H2Configuration(client_side=False, header_encoding="utf-8")

    __slots__ = ("conn", "_streams")

    def __init__(self):
        self.conn = H2Connection(config=self.config)
        self._streams: Dict[int, Request] = {}

    def connect(self) -> bytes:
        self.conn.initiate_connection()
        return self.conn.data_to_send()

    def handle_request(self, data: bytes) -> Tuple[Optional[bytes], Optional[List[Request]], bool]:

        try:
            events = self.conn.receive_data(data)
        except ProtocolError as e:
            return self.conn.data_to_send(), None, True

        to_send_data, requests, close = self.conn.data_to_send(), [], False
        for event in events:
            if isinstance(event, RequestReceived):
                self._streams[event.stream_id] = _get_request_from_event(event)
            elif isinstance(event, DataReceived):
                if event.stream_id in self._streams:
                    self._streams[event.stream_id]._body += event.data
            elif isinstance(event, StreamEnded):
                requests.append(self._streams.get(event.stream_id))
            elif isinstance(event, ConnectionTerminated):
                # Stop all requests
                close = True
            # elif isinstance(event, StreamReset):
            #     self.stream_reset(event.stream_id)

            # FLOW CONTROL

            # elif isinstance(event, WindowUpdated):
            #     self.window_updated(event.stream_id, event.delta)
            # elif isinstance(event, RemoteSettingsChanged):
            #     if SettingCodes.INITIAL_WINDOW_SIZE in event.changed_settings:
            #         self.window_updated(None, 0)

        to_send_data += self.conn.data_to_send()
        return to_send_data, requests, close

    def handle_response(self, response: Response, request: Request):
        response.headers[b"content-length"] = str(len(response.body)).encode()
        response_headers = ((":status", str(response.status)),) + tuple(response.headers.items())
        self.conn.send_headers(request.stream, response_headers)
        data = response.body
        while True:

            chunk_size = len(data)
            try:
                self.conn.send_data(request.stream, data[:chunk_size], end_stream=(chunk_size >= len(data)))
            except (StreamClosedError, ProtocolError):
                # The stream got closed and we didn't get told. We're done
                # here.
                break

            yield self.conn.data_to_send()
            data = data[chunk_size:]
            if not data:
                return
