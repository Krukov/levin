import dataclasses
import inspect
import linecache
import sys
import time
from typing import Any, Callable, Iterable, Tuple

# https://github.com/what-studio/profiling/blob/master/profiling/tracing/__init__.py
# https://github.com/mgedmin/profilehooks/blob/master/profilehooks.py
# https://github.com/what-studio/profiling/
# https://github.com/nvdv/vprof

# https://docs.python.org/3.7/library/sys.html?highlight=setprofile#sys.setprofile
# http://www.dalkescientific.com/writings/diary/archive/2005/04/20/tracing_python_code.html


@dataclasses.dataclass()
class CallResult:
    code: str
    line: int
    file: str
    start: float
    end: float = 0.0

    @property
    def time(self):
        return self.end - self.start


class Profile:
    def __init__(self, func: Callable):
        self._func = self._get_code_alias(func.__code__)
        self._lines = []
        self._start = time.time()

    def _filter_frame(self, frame):
        return self._get_code_alias(frame.f_code) == self._func

    @staticmethod
    def _get_code_alias(code):
        return code.co_filename, code.co_firstlineno, code.co_name

    def trace(self, frame, event, arg):
        if event == "line" and self._filter_frame(frame):
            lineno = frame.f_lineno
            filename = frame.f_code.co_filename
            line = linecache.getline(filename, lineno)
            if self._lines:
                self._lines[0].end = time.time()
            self._lines.append(CallResult(code=line, line=lineno, file=filename, start=time.time()))
        return self.trace

    def get_lines(self):
        return self._lines


def profile_func(func: Callable, *args, **kwargs) -> Tuple[Any, Profile]:
    _profile = Profile(func)
    orig_trace = sys.gettrace()
    sys.settrace(_profile.trace)
    try:
        result = func(*args, **kwargs)
    finally:
        sys.settrace(orig_trace)
    return result, _profile


def get_func_meta(func: Callable):
    pass


def get_func_code_lines(func: Callable) -> Iterable[Tuple[int, str]]:
    return inspect.getsourcelines(func)


def match_code_with_stats(func):
    pass
