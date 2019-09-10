import re
import time

from levin.utils.profile import profile_func


def simple(text="text"):
    time.sleep(1)
    a = re.match(r"text|foo", text)
    if a:
        return a


def deep():
    s = "test"

    def _in():
        return simple(s)

    return _in()


def with_recursion(i=0):
    if i < 10:
        return with_recursion(i + 1)
    return simple()


class Some:
    def method(self):
        return simple()


def test_simple_func_profile():
    res, profile_result = profile_func(simple)
    assert res is not None
    assert profile_result is not None

    result = profile_result.get_lines()

    assert result[0].code == "    time.sleep(1)\n"
    assert result[0].line == 8
    assert result[0].file == __file__
    assert 1 < result[0].time < 1.1
    assert len(result) == 4
