import asyncio
import time
from functools import partial
from typing import Callable

from levin.core.common import Request
from levin.core.component import Component
from levin.utils.profile import SimpleProfile, print_result


class ProfileHandler(Component):
    name = "profile"

    threshold: float = 0.1
    get_time: Callable = time.perf_counter
    depth: int = 1
    callback = print_result

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._targets = []
        self._lock = asyncio.Lock()

    @staticmethod
    def request_hash(request: Request):
        return request.path + request.method

    async def middleware(self, request: Request, handler, call_next):
        if self.request_hash(request) in self._targets and not self._lock.locked():
            async with self._lock:
                profile = SimpleProfile(depth=self.depth, memory=True)
                handler = partial(profile.run, handler)
                try:
                    return await call_next(request, handler)
                finally:
                    self.callback(profile)
        start = self.get_time()
        try:
            return await call_next(request, handler)
        finally:
            if (self.get_time() - start) > self.threshold:
                self._targets.append(self.request_hash(request))
