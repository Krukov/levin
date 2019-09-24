import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from levin.core.component import Component


class SyncToAsync(Component):
    def __init__(self, max_workers=10):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=__name__)

    def stop(self, app):
        self._executor.shutdown(wait=True)

    async def middleware(self, request, handler):  # should be last
        if not asyncio.iscoroutinefunction(handler):
            return await asyncio.get_running_loop().run_in_executor(self._executor, handler, request)
        return await handler(request)


class RunProcess(Component):
    def __init__(self, max_workers=10):
        self._executor = ProcessPoolExecutor(max_workers=max_workers)

    def stop(self, app):
        self._executor.shutdown(wait=True)

    async def middleware(self, request, handler):  # should be last
        if request.get("process", False):
            return await asyncio.get_running_loop().run_in_executor(self._executor, handler, request)
        return await handler(request)
