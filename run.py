import asyncio, time
from levin.app import Application
import faulthandler
import uvloop
uvloop.install()

app = Application()


@app.get(b"/-/")
def root(request):
    return {"status": "ok"}


@app.get(b"/{user}/")
def user(request):
    return {"status": request['user'].decode()}


@app.post(b"/-/")
async def post_root(request):
    await asyncio.sleep(3)
    return {"status": "20"}


@app.delete(b"/-/")
async def del_root(request):
    time.sleep(100)
    return {"status": "20"}


def main():
    faulthandler.enable()
    try:
        app.run("0.0.0.0", 8000, app_loop=True, debug=False)
    except:
        raise


if __name__ == '__main__':
    main()
