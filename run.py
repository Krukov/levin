import asyncio
import time
from levin import app

import faulthandler
# import uvloop
# uvloop.install()

app.configure({
    "templates": {
        "path": "/"
    },
})


@app.route.get("/-/", name="root", status=201)
async def root(request):
    a = list(range(10000))
    await asyncio.sleep(1)
    return {"status": a}


@app.route.get("/new/{user}/")
def user(request):
    a = list(range(10000))
    time.sleep(1)
    return {"status": request.get("user")}


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
async def post_root(request):
    """
    Create something
    """
    await asyncio.sleep(1)
    return {"status": "20"}


@app.route.delete(b"/-/", process=True)
def del_root(request):
    time.sleep(1)
    return {"status": "20"}


def main():
    faulthandler.enable()
    app.run(8000)


if __name__ == '__main__':
    app.cli()
    main()
