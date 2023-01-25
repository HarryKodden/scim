from fastapi import FastAPI

app = FastAPI(title="SCIM Sample")


@app.get("/Group")
async def get_all_groups():
    pass


@app.post("/Group")
async def create_group():
    pass


@app.get("/Group/{id}")
async def get_group(id: str):
    pass


@app.put("/Group/{id}")
async def update_group(id: str):
    pass


@app.delete("/Group/{id}")
async def delete_group(id: str):
    pass


@app.get("/User")
async def get_all_users():
    pass


@app.post("/User")
async def create_user():
    pass


@app.get("/User/{id}")
async def get_user(id: str):
    pass


@app.put("/User/{id}")
async def update_user(id: str):
    pass


@app.delete("/User/{id}")
async def delete_user(id: str):
    pass


@app.on_event("startup")
def startup():
    pass


@app.on_event("shutdown")
def shutdown():
    pass
