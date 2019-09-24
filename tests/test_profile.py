import time

import pytest

from . import samples
from levin.utils.profile import SimpleProfile


def test_simple_profile_simple():
    profile_result = SimpleProfile()
    profile_result.run(samples.simple)

    result = list(profile_result.get_lines())

    assert len(result) == 4

    assert result[0].code == "    time.sleep(0.1)\n"
    assert result[0].func_line == 1
    assert result[0].filename == samples.__file__
    assert 0.1 < result[0].time < 0.2

    assert result[1].code.strip() == 'a = re.match(r"text|foo", text)'
    assert result[1].func_line == 2

    # assert result[2].code.strip() == "if a:"
    # assert result[2].func_line == 4
    #
    # assert result[3].code.strip() == "return a"
    # assert result[3].func_line == 5


def test_simple_profile_deep():
    profile_result = SimpleProfile()
    profile_result.run(samples.deep)

    result = profile_result.get_lines()

    assert len(result) == 4, result

    assert result[0].code.strip() == 's = "test"'
    assert result[0].func_line == 1
    assert result[0].filename == samples.__file__

    assert result[1].code.strip() == "def _in():"
    assert result[1].func_line == 3

    assert result[3].code.strip() == "return _in() or s"
    assert result[3].func_line == 6

    assert 0.1 < result[3].time < 0.2


def test_deep_func_simple_profile_2():
    profile_result = SimpleProfile(depth=2)
    profile_result.run(samples.deep)

    result = profile_result.get_lines()

    assert result[0].code.strip() == 's = "test"'
    assert result[0].func_line == 1
    assert result[0].depth == 1
    assert result[0].filename == samples.__file__

    assert result[1].code.strip() == "def _in():"
    assert result[1].depth == 1
    assert result[1].func_line == 3

    assert result[3].code.strip() == "return _in() or s"
    assert result[3].depth == 1
    assert result[3].func_line == 6

    assert result[4].code.strip() == "return simple(s)"
    assert result[4].depth == 2
    assert result[4].func_line == 1

    assert 0.1 < result[4].time < 0.2
    assert 0.1 < result[3].time < 0.2
    assert len(result) == 5, profile_result._target_func


def test_deep_func_simple_profile_3():
    profile_result = SimpleProfile(depth=3)
    profile_result.run(samples.deep)

    result = profile_result.get_lines()

    assert result[0].code.strip() == 's = "test"'
    assert result[0].func_line == 1
    assert result[0].filename == samples.__file__

    assert result[1].code.strip() == "def _in():"
    assert result[1].func_line == 3

    assert result[3].code.strip() == "return _in() or s"
    assert result[3].func_line == 6
    assert result[3].depth == 1

    assert result[4].code.strip() == "return simple(s)"
    assert result[4].depth == 2
    assert result[4].func_line == 1

    assert result[5].code.strip() == "time.sleep(0.1)"
    assert result[5].depth == 3
    assert result[5].func_line == 1

    assert 0.1 < result[5].time < 0.2
    assert 0.1 < result[4].time < 0.2
    assert 0.1 < result[3].time < 0.2
    assert len(result) == 9, result


def test_with_recursion_func_simple_profile():
    profile_result = SimpleProfile()
    profile_result.run(samples.with_recursion)

    result = profile_result.get_lines()
    assert len(result) == 3

    assert result[0].code.strip() == "if i < 5:"
    assert result[0].func_line == 1
    assert result[0].filename == samples.__file__

    assert result[1].code.strip() == "return with_recursion(i + 1)"
    assert result[1].func_line == 2

    assert 0.1 < result[2].time < 0.2


def test_with_recursion_func_simple_profile_depth2():
    profile_result = SimpleProfile(depth=2)
    profile_result.run(samples.with_recursion)

    result = profile_result.get_lines()
    assert len(result) == 6, result

    assert result[0].code.strip() == "if i < 5:"
    assert result[0].func_line == 1
    assert result[0].depth == 1
    assert result[0].filename == samples.__file__

    assert result[1].code.strip() == "return with_recursion(i + 1)"
    assert result[1].depth == 1
    assert result[1].func_line == 2

    assert result[3].code.strip() == "if i < 5:"
    assert result[3].func_line == 1
    assert result[3].depth == 2
    assert result[3].filename == samples.__file__

    assert result[4].code.strip() == "return with_recursion(i + 1)"
    assert result[4].func_line == 2
    assert result[4].depth == 2

    assert 0.1 < result[1].time < 0.2
    # assert 0.1 < result[4].time < 0.2


def test_method_simple_profile():
    profile_result = SimpleProfile()
    profile_result.run(samples.Some().method, text="test")

    result = profile_result.get_lines()

    assert len(result) == 3, result
    assert result[0].code.strip() == "if simple(text):"
    assert result[0].func_line == 1
    assert result[0].filename == samples.__file__
    assert 0.1 < result[0].time < 0.2

    assert result[2].code.strip() == "return True"
    assert result[2].func_line == 3


def test_method_simple_profile_exception():
    profile_result = SimpleProfile()
    with pytest.raises(Exception):
        profile_result.run(samples.Some().method, text="foo")

    result = profile_result.get_lines()

    assert len(result) == 3
    assert result[0].code.strip() == "if simple(text):"
    assert result[0].func_line == 1
    assert result[0].filename == samples.__file__
    assert 0.1 < result[0].time < 0.2

    assert result[1].code.strip() == 'raise Exception("test")'
    assert result[1].func_line == 2


@pytest.mark.asyncio
async def test_simple_profile_aio():
    profile_result = SimpleProfile()
    await profile_result.run(samples.simple_aio)

    result = profile_result.get_lines()

    assert len(result) == 1
    assert result[0].code.strip() == "await asyncio.sleep(0.1)"
    assert result[0].func_line == 1
    assert result[0].depth == 1
    assert result[0].filename == samples.__file__
    assert 0.1 < result[0].time < 0.2, result[0].end


@pytest.mark.asyncio
async def test_deep_aio_simple():
    profile_result = SimpleProfile()
    await profile_result.run(samples.adeep)

    result = profile_result.get_lines()

    assert len(result) == 3

    assert result[0].code.strip() == "await simple_aio()"
    assert result[0].func_line == 1
    assert result[0].filename == samples.__file__
    assert 0.1 < result[0].time < 0.2

    assert result[1].code.strip() == 'print("Hi")'
    assert result[1].func_line == 2

    assert result[2].code.strip() == "await simple_aio()"
    assert result[2].func_line == 3
    assert 0.1 < result[2].time < 0.2


@pytest.mark.asyncio
async def test_deep_aio_2_simple():
    profile_result = SimpleProfile(2)
    await profile_result.run(samples.adeep)

    result = profile_result.get_lines()

    assert len(result) == 4, result

    assert result[0].code.strip() == "await simple_aio()"
    assert result[0].func_line == 1
    assert result[0].filename == samples.__file__
    assert 0.1 < result[0].time < 0.2, profile_result._calls

    assert result[1].code.strip() == 'print("Hi")', result
    assert result[1].func_line == 2
    assert result[1].depth == 1

    assert result[2].code.strip() == "await simple_aio()"
    assert result[2].func_line == 3
    assert result[2].filename == samples.__file__

    assert result[3].code.strip() == "await asyncio.sleep(0.1)", result
    assert result[3].func_line == 1
    assert result[3].depth == 2
    assert 0.1 < result[3].time


def test_func_simple_profile_overhead():
    profile_result = SimpleProfile()
    t1 = time.time()
    samples.simple()
    t2 = time.time()
    profile_result.run(samples.simple)
    t3 = time.time()
    print(t3 - t2, sum([l.time for l in profile_result.get_lines()]))
    assert ((t3 - t2) - (t2 - t1)) * 100 / (t2 - t1) < 5, ((t3 - t2) - (t2 - t1)) * 100 / (t2 - t1)
    assert sum([l.time for l in profile_result.get_lines()]) < (t3 - t2) * 1.1


def test_memory_simple():
    profile_result = SimpleProfile(memory=True)
    profile_result.run(samples.memory_simple)
    result = profile_result.get_lines()

    assert len(result) == 2, result
    assert result[0].mem > 0, result
