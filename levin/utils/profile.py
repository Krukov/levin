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
    # pylint: disable=too-many-instance-attributes
    __slots__ = ("lineno", "caller_lineno", "filename", "depth", "start", "end", "ncalls", "mem")

    def __init__(
        self,
        lineno: int,
        caller_lineno: int,
        filename: str,
        start: float,
        depth: int = 0,
        end: float = 0.0,
        ncalls: int = 0,
        mem: int = 0,
    ):  # pylint: disable=too-many-arguments
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

    # pylint: disable=too-many-instance-attributes

    CALL = "call"
    C_CALL = "c_call"
    C_RETURN = "c_return"
    EXCEPTION = "c_exception"
    C_CALLS = (C_RETURN, EXCEPTION, C_CALL)
    CALLS = (C_CALL, CALL)

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

    def _save_frame(self, frame):
        if len(self._target_func) != self._depth and self._get_code_alias(frame.f_back.f_code) in self._target_func:
            self._target_func.append(self._get_code_alias(frame.f_code))
            self._save_function(frame.f_code)

    def _get_depth_at_recursion(self, mother_frame, recursion_depth):
        depth = 0
        while self._get_code_alias(mother_frame.f_code) == self._get_code_alias(mother_frame.f_back.f_code):
            depth += 1
            mother_frame = mother_frame.f_back
        if depth >= recursion_depth or depth == 0:
            return None
        return depth

    def _get_current_depth(self, event, frame):
        frame = self._get_event_frame(event, frame)
        code_alias = self._get_code_alias(frame.f_code)
        self._save_frame(frame)

        if code_alias in self._target_func:
            indexes = [index for index, func in enumerate(self._target_func) if func == code_alias]
            if len(indexes) > 1:  # recursion
                return self._get_depth_at_recursion(frame, len(indexes))
            return indexes.pop() + 1
        return None

    def _get_the_same_call(self, frame, depth):
        new_call = self._create_call_from(frame, depth)
        for call in self._calls:
            if self._is_the_same_call(new_call, call):
                return call
        return None

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
            return self._trace
        # SKIP DEPTH IF IT == 1
        depth = self._get_current_depth(event, frame)
        if depth is None:
            return self._trace
        target_frame = self._get_event_frame(event, frame)

        if event in self.CALLS:
            self._trace_call(target_frame, depth)
        else:
            call = self._get_the_same_call(target_frame, depth)
            call.end = time.time()
        return self._trace

    def _trace_call(self, target_frame, depth):
        call = self._get_the_same_call(target_frame, depth)
        if not call:
            self._calls.append(self._create_call_from(target_frame, depth))
        else:
            call.ncalls += 1

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
        return self.trace(func)(*args, **kwargs)

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

    # def get_lines(self):
    #     lines = {(call.lineno, call.filename, call.depth): call for call in self._calls}
    #     for depth, (func_filename, func_lineno, _) in enumerate(self._target_func, start=1):
    #         for lineno, text_line in enumerate(
    #             self._get_function(func_filename, func_lineno).splitlines()[1:], start=1
    #         ):
    #             if not text_line.strip():
    #                 continue
    #             line = self._get_line(
    #                 lines.get((lineno + func_lineno, func_filename, depth)), lineno, func_lineno, func_filename
    #             )
    #             line.depth = depth
    #             line.mem = self._get_memory_for_call(line)
    #             lines[(line.lineno, line.filename, line.depth)] = line
    #     return sorted(lines.values(), key=lambda c: (c.filename, c.start))
    #
    # def _get_line(self, line, lineno, func_lineno, func_filename):
    #     if not line:
    #         line = CallResult(lineno=lineno + func_lineno, filename=func_filename, start=0, caller_lineno=func_lineno)
    #     line.mem = self._get_memory_for_call(line)
    #     return line

    def get_tree_of_calls(self):
        calls = []
        func_filename, func_lineno, _ = self._target_func[0]
        target_call = CallResult(lineno=func_lineno, filename=func_filename, start=0, caller_lineno=func_lineno, depth=0)
        self._get_call_deep(target_call, calls)
        return calls

    get_lines = get_tree_of_calls

    def _get_call_deep(self, call: CallResult, calls):
        for lineno, text_line in enumerate(
                self._get_function(call.filename, call.lineno).splitlines()[1:], start=1
        ):
            if not text_line.strip():
                continue
            line = self._get_call(lineno, call.lineno, call.filename, call.depth + 1)
            for called in self._get_called_from_line(line):
                self._get_call_deep(called, calls)
            calls.append(line)

    def _get_called_from_line(self, line: CallResult):
        print("LINE:", line)
        for call in self._calls:
            print("->", call, call.caller_lineno)
            if call.depth == line.depth + 1 and call.caller_lineno == line.func_line:
                yield call

    def _get_call(self, lineno, func_lineno, func_filename, depth):
        for call in self._calls:
            if call.lineno == lineno + func_lineno and call.filename == func_filename and call.depth == depth:
                return call
        return CallResult(lineno=lineno + func_lineno, filename=func_filename, start=0, caller_lineno=func_lineno, depth=depth)


def print_result(profile: SimpleProfile):
    filename = None
    for line in profile.get_tree_of_calls():
        if filename != line.filename:
            filename = line.filename
            print(f"--> {filename}")
        TAB = '\t'
        if line.mem or line.time:
            print(f"{line.lineno}: {TAB * line.depth}{line.code} {TAB} <- {line.time}s; {line.mem}B nc {line.ncalls} - {line.start}")
        else:
            print(f"{line.lineno}: {TAB * line.depth}{line.code}")
