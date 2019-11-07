import asyncio
import pytest
from levin.core.connection import Connection
from levin.core.common import Request
from unittest.mock import Mock


def test_full_connection_lifecycle():
    parser = Mock()
    parser.handle_request = Mock(return_value=(b"resp", [], True))
    handler = Mock()
    transport = Mock()
    connection = Connection(parsers=[parser], handler=handler)

    connection.connection_made(transport)
    parser.connect.assert_called_once()

    connection.data_received(b"data")

    handler.assert_not_called()
    parser.handle_request.assert_called_once()
    transport.write.assert_called_once_with(b"resp")
    transport.close.assert_called_once()


@pytest.mark.asyncio
async def test_full_connection_lifecycle_with_resp(event_loop):
    parser = Mock()
    request = Request(b"/path")
    parser.handle_request = Mock(return_value=(b"", [request], True))
    parser.handle_response = Mock(return_value=[b"test", ])

    async def handler(request):
        assert request.raw_path == b"/path"
        assert request.method == b"GET"
        return

    transport = Mock()
    connection = Connection(parsers=[parser], handler=handler, loop=event_loop)

    connection.connection_made(transport)
    parser.connect.assert_called_once()

    connection.data_received(b"-")

    await asyncio.sleep(0.01, loop=event_loop)  # switch task - allow handler execute

    parser.handle_request.assert_called_once()
    transport.write.assert_called_once_with(b"test")
    transport.close.assert_called_once()



