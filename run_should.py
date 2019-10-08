import asyncio, time
import dataclasses
from levin import app
# import uvloop
# uvloop.install()

app.configure({
    "route.append_slash": True,
}, from_env="/test/env.file")


@app.route.get("/-/")
async def simple():
    return {"status": "ok"}


@app.route.get("/{user}/", user=UUID)
async def user(request):
    return {"status": request['user']}


@dataclasses.dataclass
class Data:
    test: bool
    some: str

from levin.core.app import route

@route.post("/-/", db_session=False, auth=True, push=Push.get("/{user.uid}/"))
async def post_root(data: Data, user):
    await asyncio.sleep(100)
    return {"status": data.test, "user": user.uid}


@route.delete("/-/", lala=Schema, qwery={"user": UUID})
def block(**lala):
    time.sleep(100)
    return {"status": "20"}


app2 = ProfApplication(app)

@app2.get("status", )
async def status():
    return await db.status



def main():
    app.run(sub_apps=(app2, ))


if __name__ == '__main__':
    main()
