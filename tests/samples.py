import asyncio
import re
import time


def simple(text="text"):
    time.sleep(0.1)
    a = re.match(r"text|foo", text)

    if a:
        return a


def deep():
    s = "test"

    def _in():
        return simple(s)

    return _in() or s


def with_recursion(i=0):
    if i < 5:
        return with_recursion(i + 1)
    return simple()


class Some:
    def method(self, text):
        if simple(text):
            raise Exception("test")
        return True


async def adeep():
    await simple_aio()
    print("Hi")
    await simple_aio()


async def simple_aio():
    await asyncio.sleep(0.1)


def memory_simple():
    a = list(range(1000))
    return a
