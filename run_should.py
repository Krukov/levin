import asyncio, time
import dataclasses
from levin.core.server import run, server
import faulthandler
# import uvloop
# uvloop.install()

@app.route.get("/-/")
async def simple():
    return {"status": "ok"}


@app.route.get("/{user}/")
async def user(request):
    return {"status": request['user']}


@dataclasses.dataclass
class Data:
    test: bool
    some: str

from levin.core.app import route

@route.post("/-/", db_session=True, auth=True, push=Push.get("/{user.uid}/", ))
async def post_root(data: Data, user):
    await asyncio.sleep(100)
    return {"status": data.test, "user": user.uid}


@route.delete("/-/")
def block():
    time.sleep(100)
    return {"status": "20"}


app2 = ProfApplication(app)

@app2.get("status", )
async def status():
    return await db.status



def main():
    faulthandler.enable()
    run(server(app, 8000), server(app2, 9000))


if __name__ == '__main__':
    main()
