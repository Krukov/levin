#!/usr/bin/env python
import time
from levin import app
import ujson
import faulthandler
# import uvloop
# uvloop.install()
import typing

app.configure({
    "templates": {
        "path": "/",
        "enable": False,
    },
    "json_format": {
        "json_dumps": ujson.dumps,
        "default": None,
    },
    "process_executor": {
        "max_workers": 1
    },
    "push": {
        "enable": False,
    },
    "profile": {
        "enable": False
    },
})


@app.route.get("/-/", name="root", status=201, push="/q/")
async def root():
    a = list(range(30000))
    return {"status": a}


@app.route.get("/new/{user}/p", process=True)
def userp(request):
    return {"status": request.query_params.get("str", None)}


def condition(*args, **kwargs):
    return False


@app.route.get("/new/{user}/", profile_condition=condition, name="user")
async def _user(user: app.injector.Inject("user")):
    return {"status": user, "url": app.route.url("user", user="test")}


@app.route.get("/q/")
def qwert(request):
    return {"status": request.query_params}


@app.route.get("/template/{user}/", template="index.html")
def user_template(request):
    return {"user": request.get("user")}


@app.route.get(b"/template/{user}/2")
def user_template2(request):
    return app.templates.Template(path="index.html", context={"status": request.get("user")})


@app.route.get(b"/template/{user}/3")
def user_template3(request):
    return app.templates.render(path="index.html", context={"user": request.get("user")})


@app.route.post(b"/-/", )
def post_root(request, process=True):
    """
    Create something
    """
    time.sleep(1)
    return {"status": "20"}


@app.route.delete(b"/-/", process=True)
def del_root(request):
    time.sleep(1)
    return {"status": "20"}


if __name__ == '__main__':
    faulthandler.enable()
    app.cli()
