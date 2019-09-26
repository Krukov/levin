import asyncio
import time
from levin import app

# from levin.app.route import post
# from levin.app import route
# import uvloop
# uvloop.install()


@app.route.get("/-/", name="root", status=201)
async def root(request):
    await asyncio.sleep(1)
    return {"status": "ok"}


@app.route.get(b"/new/{user}/")
def user(request, user):
    return {"status": user}


@app.route.post(b"/-/", )
async def post_root(request):
    await asyncio.sleep(1)
    return {"status": "20"}


@app.route.delete(b"/-/", process=True)
def del_root(request):
    time.sleep(1)
    import sys
    print(sys.getgid())
    return {"status": "20"}


def main():
    # faulthandler.enable()
    try:
        app.run(8000)
    except:
        raise


if __name__ == '__main__':
    main()
