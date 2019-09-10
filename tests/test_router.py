import re

from levin.request import Request
from levin.router import HttpRouter, RegexpCondition


def handler(request):
    return "handler"


def test_pattern_to_regexp():
    pattern = b"/order/{user}/{order}"
    expect = b"/order/(?P<user>[-_a-zA-Z]+)/(?P<order>[-_a-zA-Z]+)"
    result = RegexpCondition.pattern_to_regexp(pattern).pattern
    assert result == expect


def test_resolve_simple():

    router = HttpRouter()
    router.add(b"POST", b"/test1", handler)
    request = Request(path=b"/test1", method=b"POST", body=b"")
    hendler_res = router.resolve(request)

    assert hendler_res is handler
    assert request["pattern"] == b"/test1"


def test_resolve_simple_slash():
    router = HttpRouter()
    router.add(b"POST", b"/test1", handler)
    request = Request(path=b"/test1/", method=b"POST", body=b"")
    hendler_res = router.resolve(request)

    assert hendler_res is handler
    assert request["pattern"] == b"/test1"


def test_resolve_simple_slash_route():
    router = HttpRouter()
    router.add(b"POST", b"/test1/", handler)
    request = Request(path=b"/test1", method=b"POST", body=b"")
    hendler_res = router.resolve(request)

    assert hendler_res is handler
    assert request["pattern"] == b"/test1/"


def test_resolve_simple_negative():
    router = HttpRouter()
    router.add(b"POST", b"/test1", handler)

    assert router.resolve(Request(path=b"/test/", method=b"POST", body=b"")) is None
    assert router.resolve(Request(path=b"/test/test1", method=b"POST", body=b"")) is None
    assert router.resolve(Request(path=b"/test1/some", method=b"POST", body=b"")) is None
    assert router.resolve(Request(path=b"/test1", method=b"GET", body=b"")) is None


def test_resolve_pattern():
    router = HttpRouter()
    router.add(b"POST", b"/test/{user}", handler)
    request = Request(path=b"/test/myuser", method=b"POST", body=b"")
    hendler_res = router.resolve(request)

    assert hendler_res is handler
    assert request["pattern"] == b"/test/{user}"
    assert request["user"] == b"myuser"


def test_resolve_pattern_slash():
    router = HttpRouter()
    router.add(b"POST", b"/test/{user}", handler)
    request = Request(path=b"/test/myuser/", method=b"POST", body=b"")
    hendler_res = router.resolve(request)

    assert hendler_res is handler
    assert request["pattern"] == b"/test/{user}"
    assert request["user"] == b"myuser"


def test_resolve_pattern_slash_route():
    router = HttpRouter()
    router.add(b"POST", b"/test/{user}/", handler)
    request = Request(path=b"/test/myuser", method=b"POST", body=b"")
    hendler_res = router.resolve(request)

    assert hendler_res is handler
    assert request["pattern"] == b"/test/{user}/"
    assert request["user"] == b"myuser"


def test_resolve_pattern_negative():
    router = HttpRouter()
    router.add(b"POST", b"/test/{user}", handler)

    assert router.resolve(Request(path=b"/test", method=b"POST", body=b"")) is None
    assert router.resolve(Request(path=b"/testmyuser", method=b"POST", body=b"")) is None
    assert router.resolve(Request(path=b"/test/myuser/test", method=b"POST", body=b"")) is None
    assert router.resolve(Request(path=b"/v1/test/myuser", method=b"POST", body=b"")) is None


def test_resolve_pattern_re():
    router = HttpRouter()
    router.add(b"POST", re.compile(br"/test/(?P<user>\w+)/(?P<id>\d+)"), handler)
    request = Request(path=b"/test/myuser/10", method=b"POST", body=b"")
    hendler_res = router.resolve(request)

    assert hendler_res is handler
    assert request["pattern"] == b"/test/{user}/{id}"
    assert request["user"] == b"myuser"
    assert request["id"] == b"10"
