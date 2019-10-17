import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import partial

from levin.core.component import Component


class _Executor(Component):
    executor_class = ThreadPoolExecutor
    executor_kwargs = {}
    max_workers = 50
    _run = False

    def start(self, app):
        self._executor = self.executor_class(max_workers=self.max_workers, **self.executor_kwargs)

    def stop(self, app):
        if self._run:
            self._executor.shutdown(wait=True)

    @staticmethod
    def condition(request, handler):
        return True

    def middleware(self, request, handler, call_next):
        if self.condition(request, handler):
            self._run = True
            handler = partial(asyncio.get_running_loop().run_in_executor, self._executor, handler)
        return call_next(request, handler)


class SyncToAsync(_Executor):
    name = "sync_to_async"
    executor_kwargs = {"thread_name_prefix": __name__}

    @staticmethod
    def condition(request, handler):
        return not asyncio.iscoroutinefunction(handler)


class RunProcess(_Executor):
    name = "process_executor"
    executor_class = ProcessPoolExecutor
    max_workers = 2 * multiprocessing.cpu_count() + 1

    @staticmethod
    def condition(request, handler):
        return request.get("process", False)
