from fastapi import FastAPI

app = FastAPI()


@app.get("/-/")
async def root():
    return {"status": "ok"}


@app.get("/{user}/")
async def root(user: str):
    return {"status": user}

