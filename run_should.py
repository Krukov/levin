import asyncio, time
import dataclasses
from levin.app import Application
from levin.server import
import faulthandler
# import uvloop
# uvloop.install()

app = Application(middlewares=(Data, Auth, Session))


@app.get("/-/")
async def simple():
    return {"status": "ok"}


@app.get("/{user}/")
async def user(request):
    return {"status": request['user']}


@dataclasses.dataclass
class Data:
    test: bool
    some: str


@app.post("/-/", db_session=True, auth=True, push=Push.get("/{user.uid}/", ))
async def post_root(data: Data, user):
    await asyncio.sleep(100)
    return {"status": data.test, "user": user.uid}


@app.delete("/-/")
def block():
    time.sleep(100)
    return {"status": "20"}


app2 = ProfApplication(app)

@app2.get("status", )
async def status():
    return await db.status



def main():
    faulthandler.enable()
    run(server(app, 8000, runner=ThreadedLoop), server(app2, 9000, "/-/", debug=True))


if __name__ == '__main__':
    main()
