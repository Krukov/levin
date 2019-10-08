import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import partial

from levin.core.component import Component


class _Executor(Component):
    executor_class = ThreadPoolExecutor
    executor_kwargs = {}

    def __init__(self, max_workers=10, executor_kwargs=None):
        self._executor = self.executor_class(max_workers=max_workers, **(executor_kwargs or self.executor_kwargs))
        self._run = False

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

    @staticmethod
    def condition(request, handler):
        return request.get("process", False)
