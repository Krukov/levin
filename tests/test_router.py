import re

from levin.components.router import HttpRouter, RegexpCondition
from levin.core.common import Request


def handler(request):
    return "handler"


def not_found_handler():
    return "not_found"


def test_pattern_to_regexp():
    pattern = b"/order/{user}/{order}"
    expect = b"/order/(?P<user>[-_a-zA-Z0-9]+)/(?P<order>[-_a-zA-Z0-9]+)"
    result = RegexpCondition.pattern_to_regexp(pattern).pattern
    assert result == expect


def test_resolve_simple():

    router = HttpRouter(not_found_handler=not_found_handler)
    router.add(b"POST", b"/test1", handler)
    request = Request(path=b"/test1", method=b"POST", body=b"")
    handler_res, data = router._resolve(request)

    assert handler_res is handler
    assert data["pattern"] == b"/test1"


def test_resolve_simple_slash():
    router = HttpRouter(not_found_handler=not_found_handler)
    router.add(b"POST", b"/test1", handler)
    request = Request(path=b"/test1/", method=b"POST", body=b"")
    handler_res, data = router._resolve(request)

    assert handler_res is handler
    assert data["pattern"] == b"/test1"


def test_resolve_simple_slash_route():
    router = HttpRouter(not_found_handler=not_found_handler)
    router.add(b"POST", b"/test1/", handler)
    request = Request(path=b"/test1", method=b"POST", body=b"")
    handler_res, data = router._resolve(request)

    assert handler_res is handler
    assert data["pattern"] == b"/test1/"


def test_resolve_simple_negative():
    router = HttpRouter(not_found_handler=not_found_handler)
    router.add(b"POST", b"/test1", handler)

    assert router._resolve(Request(path=b"/test/", method=b"POST", body=b""))[0] is not_found_handler
    assert router._resolve(Request(path=b"/test/test1", method=b"POST", body=b""))[0] is not_found_handler
    assert router._resolve(Request(path=b"/test1/some", method=b"POST", body=b""))[0] is not_found_handler
    assert router._resolve(Request(path=b"/test1", method=b"GET", body=b""))[0] is not_found_handler


def test_resolve_pattern():
    router = HttpRouter(not_found_handler=not_found_handler)
    router.add(b"POST", b"/test/{user}", handler)
    request = Request(path=b"/test/myuser", method=b"POST", body=b"")
    handler_res, data = router._resolve(request)

    assert handler_res is handler
    assert data["pattern"] == b"/test/{user}"
    assert data["user"] == b"myuser"


def test_resolve_pattern_slash():
    router = HttpRouter(not_found_handler=not_found_handler)
    router.add(b"POST", b"/test/{user}", handler)
    request = Request(path=b"/test/myuser/", method=b"POST", body=b"")
    handler_res, data = router._resolve(request)

    assert handler_res is handler
    assert data["pattern"] == b"/test/{user}"
    assert data["user"] == b"myuser"


def test_resolve_pattern_slash_route():
    router = HttpRouter(not_found_handler=not_found_handler)
    router.add(b"POST", b"/test/{user}/", handler)
    request = Request(path=b"/test/myuser", method=b"POST", body=b"")
    handler_res, data = router._resolve(request)

    assert handler_res is handler
    assert data["pattern"] == b"/test/{user}/"
    assert data["user"] == b"myuser"


def test_resolve_pattern_negative():
    router = HttpRouter(not_found_handler=not_found_handler)
    router.add(b"POST", b"/test/{user}", handler)

    assert router._resolve(Request(path=b"/test", method=b"POST", body=b""))[0] is not_found_handler
    assert router._resolve(Request(path=b"/testmyuser", method=b"POST", body=b""))[0] is not_found_handler
    assert router._resolve(Request(path=b"/test/myuser/test", method=b"POST", body=b""))[0] is not_found_handler
    assert router._resolve(Request(path=b"/v1/test/myuser", method=b"POST", body=b""))[0] is not_found_handler


def test_resolve_pattern_re():
    router = HttpRouter()
    router.add(b"POST", re.compile(br"/test/(?P<user>\w+)/(?P<id>\d+)"), handler)
    request = Request(path=b"/test/myuser/10", method=b"POST", body=b"")
    handler_res, data = router._resolve(request)

    assert handler_res is handler
    assert data["pattern"] == b"/test/{user}/{id}"
    assert data["user"] == b"myuser"
    assert data["id"] == b"10"
