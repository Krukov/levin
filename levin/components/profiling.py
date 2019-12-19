import asyncio
import time
from typing import Callable

from levin.core.common import Request
from levin.core.component import Component
from levin.utils.profile import SimpleProfile, print_result


def _default_profile_condition(request: Request, time_spend: float, threshold: float):
    return time_spend > threshold


def _request_hash(request: Request):
    return request.raw_path + request.method


class ProfileHandler(Component):
    name = "profile"

    threshold: float = 0.1
    get_time: Callable = staticmethod(time.perf_counter)
    depth: int = 1
    with_memory: bool = False
    callback = staticmethod(print_result)
    profile_condition = staticmethod(_default_profile_condition)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._targets = []
        self._lock = asyncio.Lock()

    async def _run_with_profile(self, request: Request, handler, call_next):
        async with self._lock:
            self._targets.remove(_request_hash(request))

            profile = SimpleProfile(depth=request.get("depth", self.depth), memory=self.with_memory)
            profile.add_target(handler)
            handler = profile.trace(handler)
            try:
                return await call_next(request, handler)
            finally:
                self.callback(profile)

    async def middleware(self, request: Request, handler, call_next):
        if _request_hash(request) in self._targets and not self._lock.locked():
            return await self._run_with_profile(request, handler, call_next)
        start = self.get_time()
        try:
            return await call_next(request, handler)
        finally:
            if request.get("profile_condition", self.profile_condition)(
                request, self.get_time() - start, self.threshold
            ):
                request.logger.info("add to profile")
                self._targets.append(_request_hash(request))
