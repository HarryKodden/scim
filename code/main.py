# main.py

import uvicorn

from fastapi import Depends, Request, FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from routers import BASE_PATH, config, resource, schema, users, groups
from auth import api_key_auth

import os
import logging

level = logging.INFO \
    if os.environ.get('LOGLEVEL', 'INFO') == 'INFO' else logging.ERROR
logging.basicConfig(level=level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SCIM Sample",
    docs_url=BASE_PATH if BASE_PATH.startswith('/') else '/',
    redoc_url=None,
    dependencies=[Depends(api_key_auth)],
    openapi_url=BASE_PATH + '/openapi.json',
    responses={
        401: {"description": "Operation forbidden"},
        404: {"description": "Not found"},
        422: {"description": "Unprocessable input"},
    },
)

app.include_router(config.router)
app.include_router(resource.router)
app.include_router(schema.router)
app.include_router(users.router)
app.include_router(groups.router)


@app.on_event("startup")
def startup():
    pass


@app.on_event("shutdown")
def shutdown():
    pass


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    logging.error(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str}
    return JSONResponse(
        content=content,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
