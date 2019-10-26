import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from levin.core.component import Component


class _Executor(Component):
    executor_class = ThreadPoolExecutor
    executor_kwargs = {}
    max_workers = 2 * multiprocessing.cpu_count() + 1

    def start(self, app):
        self._executor = self.executor_class(max_workers=self.max_workers, **self.executor_kwargs)  # pylint: disable=attribute-defined-outside-init

    def stop(self, app):
        self._executor.shutdown(wait=True)

    @staticmethod
    def condition(request, handler):
        return True

    def _call(self, handler):
        async def _handler(request):
            return await asyncio.get_running_loop().run_in_executor(self._executor, handler, request)

        return _handler

    async def middleware(self, request, handler, call_next):
        if self.condition(request, handler):
            handler = self._call(handler)
        return await call_next(request, handler)


class SyncToAsync(_Executor):
    name = "sync_to_async"
    executor_kwargs = {"thread_name_prefix": __name__}

    @staticmethod
    def condition(request, handler):
        return not asyncio.iscoroutinefunction(handler) and not request.get("process", False)


class RunProcess(_Executor):
    name = "process_executor"
    executor_class = ProcessPoolExecutor

    @staticmethod
    def condition(request, handler):
        return request.get("process", False)
