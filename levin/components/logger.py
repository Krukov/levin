import logging
import time

from levin.core.common import Request, Response
from levin.core.component import Component

# TODO: format request and response on right way


class LoggerComponent(Component):
    name = "logger"

    level: int = logging.INFO
    logger_name: str = __name__
    message_format: str = '"%(method)s %(path)s %(protocol)s" %(status)s - %(body_size)s - %(time)s'

    @property
    def _logger(self):
        return logging.getLogger(self.logger_name)

    def start(self, app):
        formatter = logging.Formatter(fmt="%(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
        self._logger.setLevel(logging.DEBUG)
        self._logger.debug("CONFIGURING LOGGER")

    async def middleware(self, request: Request, handler, call_next) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request, handler)
        self._logger.log(
            self.level,
            self.message_format,
            {
                "status": response.status,
                "method": request.method.decode(),
                "path": request.raw_path.decode(),
                "protocol": request.protocol.decode(),
                "body_size": len(response.body),
                "time": str(time.perf_counter() - start)[:6]
            },
        )
        return response
