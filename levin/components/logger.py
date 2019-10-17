import logging

from levin.core.common import Request, Response
from levin.core.component import Component

# TODO: format request and response on right way


class LoggerComponent(Component):
    name = "logger"

    level: int = logging.INFO
    logger_name: str = __name__
    message_format: str = '%(remote_addr)s  "%(method)s %(path)s %(protocol)s" %(status)s - %(body_size)s'

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
        response: Response = await call_next(request, handler)
        self._logger.log(
            self.level,
            self.message_format,
            {
                "status": response.status,
                "method": request.method.decode(),
                "path": request.path.decode(),
                "protocol": request.protocol.decode(),
                "body_size": len(response.body),
            },
        )
        return response
