import dataclasses
import asyncio
import linecache
import sys
import time
from typing import Callable, Iterable, Tuple, List
import inspect
from cProfile import Profile as _cProfile
from importlib.util import spec_from_file_location, module_from_spec

# https://github.com/what-studio/profiling/blob/master/profiling/tracing/__init__.py
# https://github.com/mgedmin/profilehooks/blob/master/profilehooks.py
# https://github.com/what-studio/profiling/
# https://github.com/nvdv/vprof

# https://docs.python.org/3.7/library/sys.html?highlight=setprofile#sys.setprofile
# http://www.dalkescientific.com/writings/diary/archive/2005/04/20/tracing_python_code.html


@dataclasses.dataclass()
class CallResult:
    line: int
    frame_line: int
    file: str
    depth: int
    start: float
    end: float = 0.0

    @property
    def time(self):
        return self.end - self.start

    @property
    def func_line(self):
        return self.line - self.frame_line

    @property
    def code(self):
        return linecache.getline(self.file, self.line)

    @property
    def is_keyword(self):
        return self.code.strip().startswith(("def ", "class ", "try:", "if ", "elif ", "else:", "brake", "continue", "finally: ", "while", "import ", "from ", "for ", "return ", "catch "))

    def __repr__(self):
        return f"{self.time} {self.code}"


class Profile:
    def __init__(self, depth: int = 1):
        self._lines: List[CallResult] = []
        self._depth = depth
        self._current_depth = 0
        self._start = time.time()

    def trace(self, frame, event, arg):
        if event == "call":
            self._current_depth += 1
        elif event == "return":
            self._current_depth -= 1
        if not self._current_depth <= self._depth:
            return self.trace
        depth_lines = [call_result for call_result in self._lines if call_result.depth == self._current_depth]
        if event == "line":
            lineno = frame.f_lineno
            filename = frame.f_code.co_filename
            if depth_lines:
                depth_lines[-1].end = time.time()
            self._lines.append(CallResult(line=lineno, file=filename, start=time.time(), depth=self._current_depth, frame_line=frame.f_code.co_firstlineno))

        elif event in ("return", "exception") and depth_lines:
            depth_lines[-1].end = time.time()

        return self.trace

    def get_lines(self):
        return self._lines

    def run(self, func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return self._run_async(func, *args, **kwargs)
        orig_trace = sys.gettrace()
        sys.settrace(self.trace)
        try:
            result = func(*args, **kwargs)
        finally:
            sys.settrace(orig_trace)
        return result

    async def _run_async(self, func, *args, **kwargs):
        orig_trace = sys.gettrace()
        sys.settrace(self.trace)
        try:
            result = await func(*args, **kwargs)
        finally:
            sys.settrace(orig_trace)
        return result


class AsyncProfile:
    def __init__(self, depth=1):
        self._lines: List[CallResult] = []
        self._depth = depth
        self._funcs = []
        self._start = time.time()

    def _filter_frame(self, frame):
        return self._get_code_alias(frame.f_code) in self._funcs

    @staticmethod
    def _get_code_alias(code):
        return code.co_filename, code.co_firstlineno, code.co_name

    def trace(self, frame, event, arg):
        current_alias = self._get_code_alias(frame.f_code)
        if not self._filter_frame(frame):
            if event == "call":
                caller = self._get_code_alias(frame.f_back.f_code)
                if self._funcs and caller == self._funcs[-1] and len(self._funcs) < self._depth:
                    self._funcs.append(current_alias)
            return self.trace
        depth = self._funcs.index(current_alias) + 1
        depth_lines = [call_result for call_result in self._lines if call_result.depth == depth]
        if event == "line":
            lineno = frame.f_lineno
            filename = frame.f_code.co_filename
            if depth_lines:
                depth_lines[-1].end = time.time()
            self._lines.append(CallResult(line=lineno, file=filename, start=time.time(), depth=depth, frame_line=frame.f_code.co_firstlineno))
        elif event in ("return", "exception"):
            depth_lines[-1].end = time.time()

        return self.trace

    def get_lines(self):
        return self._lines

    async def run(self, func, *args, **kwargs):
        self._funcs.append(self._get_code_alias(func.__code__))
        orig_trace = sys.gettrace()
        sys.settrace(self.trace)
        try:
            result = await func(*args, **kwargs)
        finally:
            sys.settrace(orig_trace)
        return result


class cProfile:
    _func_cache = {}

    def __init__(self, depth=1):
        self._depth = depth
        self._profile = None
        self._funcs = []

    @staticmethod
    def _get_code_alias(code):
        return code.co_filename, code.co_firstlineno, code.co_name

    def run(self, func, *args, **kwargs):
        self._add_func_to_cache(func)
        self._funcs.append(self._get_code_alias(func.__code__))
        self._profile = _cProfile()
        if asyncio.iscoroutinefunction(func):
            return self._run_async(func, *args, **kwargs)
        self._profile.enable()
        try:
            result = func(*args, **kwargs)
        finally:
            self._profile.create_stats()
        return result

    async def _run_async(self, func, *args, **kwargs):
        self._profile.enable()
        try:
            result = await func(*args, **kwargs)
        finally:
            self._profile.create_stats()
        return result

    @classmethod
    def get_real_lineno(cls, caller, func):
        func_code = cls.get_func_code(caller)
        names = [func[-1]]
        for lineno, line in enumerate(func_code.splitlines()):
            for name in names:
                if name.startswith("<built-in method builtins."):
                    name = name.replace("<built-in method builtins.", "")[:-1]
                if name + "(" in line:
                    yield (caller[1] + lineno, caller[1])
                elif name + " =" in line:
                    names.remove(name)
                elif "=" in line and name in line:
                    names.append(line.split("=")[0].strip())

    def get_lines(self):
        lines = {}
        for func, info in self._profile.stats.items():
            cc, nc, tt, ct, callers = info

            for _func in self._funcs:
                if _func in callers:
                    filename, _, _ = func
                    for lineno, frame_line in self.get_real_lineno(_func, func):
                        line = CallResult(line=lineno, file=_func[0], start=0, end=tt, depth=0, frame_line=frame_line)
                        lines[line.func_line] = line
        result = []
        target_func = self._funcs[0]
        for lineno, text_line in enumerate(self.get_func_code(target_func).splitlines()[1:], start=1):
            if not text_line.strip():
                continue
            line = lines.get(lineno)
            if not line:
                line = CallResult(line=lineno + target_func[1], file=target_func[0], start=0 , end=0, frame_line=target_func[1], depth=0)
            result.append(line)
        return result


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

    def __init__(self, depth=1):
        self._calls: List[CallResult] = []  # Storage for line call result
        self._depth = depth
        self._target_func = []

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

    def _is_the_same_call_as_last(self, frame, depth):
        call = self._create_call_from(frame, depth)
        if self._calls:
            return self._is_the_same_call(call, self._calls[-1])

    @staticmethod
    def _is_the_same_call(call_1: CallResult, call_2: CallResult):
        return call_1.depth == call_2.depth and call_1.file == call_2.file and call_1.line == call_2.line

    @staticmethod
    def _create_call_from(frame, depth) -> CallResult:
        lineno = frame.f_lineno
        filename = frame.f_code.co_filename
        frame_line = frame.f_code.co_firstlineno
        return CallResult(line=lineno, file=filename, start=time.time(), depth=depth, frame_line=frame_line)

    def trace(self, frame, event: str, arg):

        depth = self._get_current_depth(event, frame)
        if depth is None:
            return None
        target_frame = self._get_event_frame(event, frame)

        if event in self.CALLS and not self._is_the_same_call_as_last(target_frame, depth):
            self._calls.append(self._create_call_from(target_frame, depth))
        else:
            depth_lines = [call_result for call_result in self._calls if call_result.depth == depth]
            depth_lines[-1].end = time.time()
        return self.trace

    def run(self, func, *args, **kwargs):
        self._target_func.append(self._get_code_alias(func.__code__))
        if asyncio.iscoroutinefunction(func):
            return self._run_async(func, *args, **kwargs)
        orig_trace = sys.getprofile()
        sys.setprofile(self.trace)
        try:
            return func(*args, **kwargs)
        finally:
            sys.setprofile(orig_trace)

    async def _run_async(self, func, *args, **kwargs):
        orig_trace = sys.getprofile()
        sys.setprofile(self.trace)
        try:
            return await func(*args, **kwargs)
        finally:
            sys.setprofile(orig_trace)

    def get_lines(self):
        lines = {(call.line, call.file, call.depth): call for call in self._calls}
        code = func_filename = func_lineno = None
        for depth, _func in enumerate(self._target_func, start=1):
            try:
                code = inspect.getsource(get_function_by(_func[0], _func[2]))
            except AttributeError:
                depth += 1
            else:
                func_filename, func_lineno, _ = _func
            for lineno, text_line in enumerate(code.splitlines()[1:], start=1):
                if not text_line.strip():
                    continue
                line = lines.get((lineno + func_lineno, func_filename, depth))
                if not line:
                    line = CallResult(line=lineno + func_lineno, file=func_filename, start=0, end=0, frame_line=func_lineno, depth=depth)

                lines[(line.line, line.file, line.depth)] = line

        return sorted(lines.values(), key=lambda c: (c.file, c.depth, c.line))


def get_function_by(filename, name):
    spec = spec_from_file_location("tmp.module", filename)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)


def print_lines(lines: List[CallResult]):
    for line in sorted(lines, key=lambda l: l.line):
        print(f"{line.code.rstrip()} ({line.time})")
