# main.py

import uvicorn

from fastapi import Request, FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

from routers import BASE_PATH, config, resource, schema, users, groups
from schema import HealthCheck

import os
import logging

LOGLEVEL = os.environ.get('LOGLEVEL', 'ERROR').upper()
logging.basicConfig(level=LOGLEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SCIM",
    docs_url=BASE_PATH if BASE_PATH.startswith('/') else '/',
    redoc_url=None,
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

if len(BASE_PATH) > 1:
    @app.get("/")
    async def redirect():
        return RedirectResponse(url=BASE_PATH)


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


@app.get(
    "/health",
    tags=["healthcheck"],
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
)
def get_health() -> HealthCheck:
    """
    ## Perform a Health Check
    Endpoint to perform a healthcheck on.
    Returns:
        HealthCheck: Returns a JSON response with the health status
    """
    return HealthCheck(status="OK")


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
