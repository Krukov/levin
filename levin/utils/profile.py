import asyncio
import tracemalloc
import linecache
import sys
import time
from typing import List
from types import CodeType
import inspect

# https://github.com/what-studio/profiling/blob/master/profiling/tracing/__init__.py
# https://github.com/mgedmin/profilehooks/blob/master/profilehooks.py
# https://github.com/what-studio/profiling/
# https://github.com/nvdv/vprof

# https://docs.python.org/3.7/library/sys.html?highlight=setprofile#sys.setprofile
# http://www.dalkescientific.com/writings/diary/archive/2005/04/20/tracing_python_code.html


class CallResult:
    __slots__ = ("lineno", "caller_lineno", "filename", "depth", "start", "end", "ncalls", "mem")

    def __init__(self, lineno, caller_lineno, filename, depth, start, end=0, ncalls=0, mem=0):
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
        return linecache.getline(self.filename, self.lineno)

    @property
    def is_keyword(self):
        return self.code.strip().startswith(("def ", "class ", "try:", "if ", "elif ", "else:", "brake", "continue", "finally: ", "while", "import ", "from ", "for ", "return ", "catch "))

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

    def __init__(self, depth=1, memory=False):
        self._calls: List[CallResult] = []  # Storage for line call result
        self._depth = depth
        self._target_func = []
        self._functions_code = {}
        self._trace_mem = memory

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

    def trace(self, frame, event: str, arg):

        depth = self._get_current_depth(event, frame)
        if depth is None:
            return None
        target_frame = self._get_event_frame(event, frame)

        if event in self.CALLS and not self._get_the_same_call(target_frame, depth):
            self._calls.append(self._create_call_from(target_frame, depth))
        else:
            call = self._get_the_same_call(target_frame, depth)
            call.ncalls += 1
            call.end = time.time()
        return self.trace

    def run(self, func, *args, **kwargs):
        func_alias = self._get_code_alias(func.__code__)
        self._target_func.append(func_alias)
        self._save_function(func)
        if asyncio.iscoroutinefunction(func):
            return self._run_async(func, *args, **kwargs)
        orig_trace = sys.getprofile()
        sys.setprofile(self.trace)
        if self._trace_mem:
            tracemalloc.clear_traces()
            tracemalloc.start()
        try:
            return func(*args, **kwargs)
        finally:
            sys.setprofile(orig_trace)
            if self._trace_mem:
                self._trace_mem = tracemalloc.take_snapshot()
                tracemalloc.stop()

    async def _run_async(self, func, *args, **kwargs):
        orig_trace = sys.getprofile()
        sys.setprofile(self.trace)
        if self._trace_mem:
            tracemalloc.clear_traces()
            tracemalloc.start()
        try:
            return await func(*args, **kwargs)
        finally:
            sys.setprofile(orig_trace)
            if self._trace_mem:
                self._trace_mem = tracemalloc.take_snapshot()
                tracemalloc.stop()

    def _save_function(self, code):
        if not isinstance(code, CodeType):
            code = code.__code__
        self._functions_code[(code.co_filename, code.co_firstlineno)] = inspect.getsource(code)

    def _get_function(self, filename, lineno):
        return self._functions_code.get((filename, lineno))

    def _get_memory_for_call(self, call: CallResult):
        if not self._trace_mem:
            return 0
        snapshot = self._trace_mem.filter_traces((
            tracemalloc.Filter(True, call.filename, lineno=call.lineno),
        ))

        for statistic in snapshot.statistics("lineno", True):
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
                    line = CallResult(lineno=lineno + func_lineno, filename=func_filename, start=0, caller_lineno=func_lineno, depth=depth)
                line.mem = self._get_memory_for_call(line)
                lines[(line.lineno, line.filename, line.depth)] = line

        return sorted(lines.values(), key=lambda c: (c.filename, c.depth, c.lineno))


