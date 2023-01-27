import uvicorn

# main.py

from fastapi import Depends, FastAPI
from routers import users, groups
from data import init_data
from auth import get_api_key

import os
import logging

level = logging.INFO \
    if os.environ.get('LOGLEVEL', 'INFO') == 'INFO' else logging.ERROR
logging.basicConfig(level=level)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="SCIM Sample",
    docs_url='/apidoc',
    redoc_url='/redoc',
    # openapi_url=None,
    dependencies=[Depends(get_api_key)],
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


app.include_router(users.router)
app.include_router(groups.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
