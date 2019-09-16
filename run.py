import asyncio, time
from levin.app import Application
import faulthandler
import uvloop
# uvloop.install()

app = Application()


@app.get(b"/-/", name="root")
async def root(request):
    return {"status": "ok"}


@app.get(b"/new/{user}/")
def user(request):
    return {"status": request['user'].decode()}


@app.post(b"/-/")
async def post_root(request):
    await asyncio.sleep(10)
    return {"status": "20"}


@app.delete(b"/-/")
def del_root(request):
    time.sleep(55)
    return {"status": "20"}


def main():
    faulthandler.enable()
    try:
        app.run("0.0.0.0", 8000, app_loop=False, debug=False)
    except:
        raise


if __name__ == '__main__':
    main()
