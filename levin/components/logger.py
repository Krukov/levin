import logging

from levin.core.component import Component

# TODO: format request and response on right way


class LoggerComponent(Component):
    name = "logger"

    def __init__(
        self,
        logger_name=__name__,
        logger=None,
        request_level=logging.INFO,
        response_level=logging.DEBUG,
        message_format="%(request)s: %(direction)s %(method)s %(path)s %(stream)s ",
    ):
        self._logger = logger or logging.getLogger(logger_name)
        self._request_level = request_level
        self._response_level = response_level
        self._format = message_format
        self.name = self.name + "." + logger_name

    def start(self, app):
        FORMAT = "%(process)s %(thread)s: %(message)s"
        formatter = logging.Formatter(fmt=FORMAT)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
        self._logger.setLevel(logging.DEBUG)
        self._logger.debug("CONFIGURING LOGGER")

    async def middleware(self, request, handler, call_next):
        self._logger.log(self._request_level, self._format, {"direction": "->", "method": request.method.decode(), "path": request.path.decode(), "stream": request.stream, "request": id(request)})
        response = await call_next(request, handler)
        self._logger.log(self._response_level, self._format, {"direction": f"<- {response.status}", "method": request.method.decode(), "path": request.path.decode(), "stream": request.stream, "request": id(request)})
        return response
