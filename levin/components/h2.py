from typing import Union

from levin.core.common import Request, Response, Push as _Push
from levin.core.component import Component


class Push(Component):
    name = "push"
    _scope_value = "_pushes"

    async def middleware(self, request: Request, handler, call_next) -> Response:
        request.set("add_push", self._create_add_push, lazy=True)
        response: Response = await call_next(request, handler)
        if request.get(self._scope_value):
            response.pushes = request.get(self._scope_value)
        if request.get("push"):
            response.pushes.append(_Push(path=request.get("push").format(**request._scope).encode(),))
        return response

    def _create_add_push(self, request: Request):

        def add(path: Union[str, bytes], method: Union[str, bytes] = b"GET"):
            if isinstance(path, str):
                path = path.encode()
            pushes = request.get(self._scope_value, [])
            pushes.append(_Push(path, method))
            request.set(self._scope_value, pushes, rewrite=True)

        return add
