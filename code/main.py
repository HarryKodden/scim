# main.py

import os
import logging
import uvicorn

from fastapi import Request, FastAPI, status
from fastapi.responses import RedirectResponse
from schema import HealthCheck
from routers import BASE_PATH, async_results, bulk, config, feeds, resource, schema, users, groups
from scim_errors import register_scim_exception_handlers

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


@app.middleware("http")
async def log_request_auth_headers(request: Request, call_next):
    # Log only presence/shape details; never log secret header values.
    auth_header = request.headers.get("authorization")
    api_key = request.headers.get("x-api-key")

    auth_scheme = "none"
    if auth_header:
        auth_scheme = auth_header.split(" ", 1)[0].lower()

    logger.debug(
        "[REQ] %s %s?%s auth_present=%s auth_scheme=%s x_api_key_present=%s",
        request.method,
        request.url.path,
        request.url.query,
        bool(auth_header),
        auth_scheme,
        bool(api_key),
    )

    return await call_next(request)


app.include_router(config.router)
app.include_router(resource.router)
app.include_router(schema.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(bulk.router)
app.include_router(feeds.router)
app.include_router(async_results.router)

register_scim_exception_handlers(app, BASE_PATH)

if len(BASE_PATH) > 1:
    @app.get("/")
    async def redirect():
        return RedirectResponse(url=BASE_PATH)


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
