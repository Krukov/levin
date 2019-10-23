#!/usr/bin/env python
import asyncio
import time
from levin import app
import ujson
import faulthandler
# import uvloop
# uvloop.install()

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
})


@app.route.get("/-/", name="root", status=201)
async def root(request):
    a = list(range(100))
    return {"status": a}


@app.route.get("/new/{user}/p", process=True)
def userp(request):
    return {"status": request.query_params.get("str", None)}


def condition(*args, **kwargs):
    return True


@app.route.get("/new/{user}/", profile_condition=condition)
async def user(request):
    a = list(range(10000))
    await asyncio.sleep(10)
    return {"status": request.get("user")}


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
