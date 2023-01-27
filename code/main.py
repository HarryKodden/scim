import uvicorn

from fastapi import FastAPI

from routers import auth, users, groups
from data import init_data

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="SCIM Sample",
    responses={
        403: {"description": "Operation forbidden"},
        404: {"description": "Not found"},
    },
)

@app.on_event("startup")
def startup():
    init_data()
    

@app.on_event("shutdown")
def shutdown():
    pass


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)