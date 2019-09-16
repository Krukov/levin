import asyncio
import logging
import json
import traceback
from concurrent.futures import ThreadPoolExecutor

from .response import Response
from .request import Request


_logger = logging.getLogger(__name__)
FORMAT = "%(process)s %(thread)s: %(message)s"
formatter = logging.Formatter(fmt=FORMAT)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
_logger.addHandler(handler)
_logger.setLevel(logging.DEBUG)
_logger.debug('CONFIGURING LOGGER')


def format_json(dumps=json.dumps):
    async def middleware(request, handler):
        response = await handler(request)
        if not isinstance(response, Response):
            data = dumps(response).encode()
            response = Response(status=200, body=data, headers={b"content-type": b"application/json"})
        return response

    return middleware


def sync(pool=ThreadPoolExecutor(max_workers=10, thread_name_prefix=__name__)):
    async def middleware(request, handler):  # should be last
        if not asyncio.iscoroutinefunction(handler):
            return await asyncio.get_running_loop().run_in_executor(pool, handler, request)
        return await handler(request)
    return middleware


def log_request(logger=_logger, level=logging.INFO, format="%(method)s %(path)s %(stream)s"):
    async def middleware(request: Request, handler):
        logger.log(level, format, request.asdict())
        return await handler(request)
    return middleware


def log_response(logger=_logger, level=logging.INFO, format="%(status)s <- %(method)s %(path)s %(stream)s"):
    async def middleware(request: Request, handler):
        response = await handler(request)
        logger.log(level, format, {**response.asdict(), **request.asdict()})
        return response
    return middleware


def _default_on_error(request, exception):
    return Response(status=500, body=traceback.format_exc().encode())


def handle_error(on_error=_default_on_error):
    async def middleware(request: Request, handler):
        try:
            return await handler(request)
        except Exception as exc:
            response = on_error(request, exc)
            if asyncio.iscoroutine(response):
                response = await response
            return response
    return middleware
