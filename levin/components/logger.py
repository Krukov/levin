import logging
import time
from logging.config import dictConfig

from levin.core.common import Request, Response
from levin.core.component import Component

DEFAULT_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {"default": {"format": "[%(asctime)s %(levelname)s] | %(name)s | %(message)s"}},
    "handlers": {"stdout": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "default"}},
    "loggers": {__name__.split(".")[0]: {"handlers": ["stdout"], "level": "INFO"}},
}


class LoggerComponent(Component):
    name = "logger"

    level: int = logging.INFO
    logger_name: str = __name__
    message_format: str = '"%(method)s %(path)s %(protocol)s" %(status)s - %(body_size)s - %(time)s - %(stream)s - %(transport)s'
    logger_config: dict = DEFAULT_CONFIG
    extra = {}

    def init(self, app):
        if self.logger_config:
            dictConfig(self.logger_config)
        self._logger = logging.getLogger(self.logger_name)  # pylint: disable=attribute-defined-outside-init

    def start(self, app):
        self._logger.info("Start server")

    def stop(self, app):
        self._logger.info("Server stop")

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
                "time": str(time.perf_counter() - start)[:6],
                "stream": request.stream,
                "transport": request.get_transport_info(),
            },
            extra=self.extra,
        )
        return response
