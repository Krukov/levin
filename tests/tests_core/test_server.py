import asyncio
from unittest.mock import Mock

import pytest

from levin.core.server import Server, run


@pytest.fixture(scope="session")
def server():
    app = Mock()
    loop = asyncio.new_event_loop()
    s = Server(app=app, host="127.0.0.1", port=8011, loop=loop)
    stop_event = asyncio.Event(loop=loop)
    run(s, loop=loop, stop_event=stop_event, wait=False)
    yield s
    stop_event.set()


@pytest.fixture()
async def cli(server):
    server.port, server._app


@pytest.mark.asyncio
async def test_server_run(cli):
    resp = await cli.get("/")
