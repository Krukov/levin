import asyncio
import inspect
import linecache
import sys
import time
import tracemalloc
from types import CodeType
from typing import List

# https://github.com/what-studio/profiling/blob/master/profiling/tracing/__init__.py
# https://github.com/mgedmin/profilehooks/blob/master/profilehooks.py
# https://github.com/what-studio/profiling/
# https://github.com/nvdv/vprof

# https://docs.python.org/3.7/library/sys.html?highlight=setprofile#sys.setprofile
# http://www.dalkescientific.com/writings/diary/archive/2005/04/20/tracing_python_code.html


class CallResult:
    __slots__ = ("lineno", "caller_lineno", "filename", "depth", "start", "end", "ncalls", "mem")

    def __init__(
        self,
        lineno: int,
        caller_lineno: int,
        filename: str,
        depth: int,
        start: float,
        end: float = 0,
        ncalls: int = 0,
        mem: int = 0,
    ):
        self.lineno = lineno
        self.filename = filename
        self.caller_lineno = caller_lineno
        self.depth = depth
        self.start = start
        self.end = end
        self.ncalls = ncalls
        self.mem = mem

    @property
    def time(self):
        return self.end - self.start

    @property
    def func_line(self):
        return self.lineno - self.caller_lineno

    @property
    def code(self):
        return linecache.getline(self.filename, self.lineno).rstrip("\n")

    def __repr__(self):
        return f"{self.code.strip()} ({self.depth}, {self.ncalls})"


class SimpleProfile:
    """Track only by call/return/exceptions """

    CALL = "call"
    C_CALL = "c_call"
    RETURN = "return"
    C_RETURN = "c_return"
    EXCEPTION = "c_exception"
    C_CALLS = (C_RETURN, EXCEPTION, C_CALL)
    CALLS = (C_CALL, CALL)
    RETURNS = (C_RETURN, RETURN, EXCEPTION)

    def __init__(self, depth: int = 1, memory: bool = False):
        self._calls: List[CallResult] = []  # Storage for line call result
        self._depth = depth
        self._target_func = []
        self._functions_code = {}
        self._trace_mem = memory
        self._orig_trace = None
        self._trace_mem_snapshot = None
        self._stop = False

    @staticmethod
    def _get_code_alias(code):
        return code.co_filename, code.co_firstlineno, code.co_name

    def _get_event_frame(self, event, frame):
        if event in self.C_CALLS:
            return frame
        return frame.f_back

    def _get_current_depth(self, event, frame):
        frame = self._get_event_frame(event, frame)
        code_alias = self._get_code_alias(frame.f_code)
        if len(self._target_func) != self._depth and self._get_code_alias(frame.f_back.f_code) in self._target_func:
            self._target_func.append(self._get_code_alias(frame.f_code))
            self._save_function(frame.f_code)

        if code_alias in self._target_func:
            indexes = [i for i, func in enumerate(self._target_func) if func == code_alias]
            if len(indexes) > 1:  # recursion
                mother_frame = frame
                i = 0
                while self._get_code_alias(mother_frame.f_code) == self._get_code_alias(mother_frame.f_back.f_code):
                    i += 1
                    mother_frame = mother_frame.f_back
                if i >= len(indexes) or i == 0:
                    return
                return i
            return indexes.pop() + 1

    def _get_the_same_call(self, frame, depth):
        new_call = self._create_call_from(frame, depth)
        for call in self._calls:
            if self._is_the_same_call(new_call, call):
                return call

    @staticmethod
    def _is_the_same_call(call_1: CallResult, call_2: CallResult):
        return call_1.depth == call_2.depth and call_1.filename == call_2.filename and call_1.lineno == call_2.lineno

    @staticmethod
    def _create_call_from(frame, depth) -> CallResult:
        lineno = frame.f_lineno
        filename = frame.f_code.co_filename
        frame_line = frame.f_code.co_firstlineno
        return CallResult(lineno=lineno, filename=filename, start=time.time(), depth=depth, caller_lineno=frame_line)

    def _trace(self, frame, event: str, arg):
        if frame is None:
            return self.trace
        # SKIP DEPTH IF IT == 1
        depth = self._get_current_depth(event, frame)
        if depth is None:
            return self.trace
        target_frame = self._get_event_frame(event, frame)

        if event in self.CALLS:
            call = self._get_the_same_call(target_frame, depth)
            if not call:
                self._calls.append(self._create_call_from(target_frame, depth))
            else:
                call.ncalls += 1
        else:
            call = self._get_the_same_call(target_frame, depth)
            call.end = time.time()
        return self._trace

    def trace(self, func):
        self._orig_trace = sys.getprofile()
        if asyncio.iscoroutinefunction(func):
            async def _wrap(*args, **kwargs):
                return await self._run_async(func, *args, **kwargs)
        else:
            def _wrap(*args, **kwargs):
                return self._run(func, *args, **kwargs)
        return _wrap

    def run(self, func, *args, **kwargs):
        self.add_target(func)
        return self.trace(func, *args, **kwargs)
        
    def add_target(self, func):
        func_alias = self._get_code_alias(func.__code__)
        self._target_func.append(func_alias)
        self._save_function(func)

    def _run(self, func, *args, **kwargs):
        self.start_trace()
        try:
            return func(*args, **kwargs)
        finally:
            self.stop()

    async def _run_async(self, func, *args, **kwargs):
        self.start_trace()
        try:
            return await func(*args, **kwargs)
        finally:
            self.stop()
    
    def start_trace(self):
        sys.setprofile(self._trace)
        if self._trace_mem:
            tracemalloc.clear_traces()
            tracemalloc.start()

    def stop(self):
        if self._stop:
            return
        sys.setprofile(self._orig_trace)
        if self._trace_mem:
            self._trace_mem_snapshot = tracemalloc.take_snapshot()
            tracemalloc.stop()
        self._stop = True

    def _save_function(self, code):
        if not isinstance(code, CodeType):
            code = code.__code__
        self._functions_code[(code.co_filename, code.co_firstlineno)] = inspect.getsource(code)

    def _get_function(self, filename, lineno):
        return self._functions_code.get((filename, lineno))

    def _get_memory_for_call(self, call: CallResult):
        if not self._trace_mem:
            return 0
        snapshot = self._trace_mem_snapshot.filter_traces(
            (tracemalloc.Filter(True, call.filename, lineno=call.lineno),)
        )

        for statistic in snapshot.statistics("lineno", False):
            for frame in statistic.traceback:
                if frame.filename == call.filename and frame.lineno == call.lineno:
                    return statistic.size
        return 0

    def get_lines(self):
        lines = {(call.lineno, call.filename, call.depth): call for call in self._calls}
        for depth, _func in enumerate(self._target_func, start=1):
            func_filename, func_lineno, _ = _func
            code = self._get_function(func_filename, func_lineno)
            for lineno, text_line in enumerate(code.splitlines()[1:], start=1):
                if not text_line.strip():
                    continue
                line = lines.get((lineno + func_lineno, func_filename, depth))
                if not line:
                    line = CallResult(
                        lineno=lineno + func_lineno,
                        filename=func_filename,
                        start=0,
                        caller_lineno=func_lineno,
                        depth=depth,
                    )
                line.mem = self._get_memory_for_call(line)
                lines[(line.lineno, line.filename, line.depth)] = line

        return sorted(lines.values(), key=lambda c: (c.filename, c.depth, c.lineno))


def print_result(profile: SimpleProfile):
    filename = None
    for line in profile.get_lines():
        if filename != line.filename:
            filename = line.filename
            print(f"--> {filename}")
        if line.mem or line.time:
            print(f"{line.lineno}: {line.code} \t <- {line.time}s; {line.mem}B nc {line.ncalls}")
        else:
            print(f"{line.lineno}: {line.code}")


def profile(func):
    p = SimpleProfile(memory=True)

    def _func(*args, **kwargs):
        try:
            return p.run(func, *args, **kwargs)
        finally:
            print_result(p)

    return _func
