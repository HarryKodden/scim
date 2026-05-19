# scim_errors.py

"""RFC 7644 SCIM Error responses and exception handlers."""

from typing import Any, Optional, Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from schema import SCIM_API_MESSAGES, SCIM_CONTENT_TYPE

SCIM_ERROR_SCHEMA = f"{SCIM_API_MESSAGES}:Error"
SCIM_EVENTS_EXTENSION = (
    "urn:ietf:params:scim:schemas:extension:events:2.0:ServiceProviderConfig"
)


def build_scim_error(
    status_code: int,
    detail: str,
    *,
    scim_type: Optional[str] = None,
) -> dict[str, Any]:
    """Build a RFC 7644 Error resource."""
    body: dict[str, Any] = {
        "schemas": [SCIM_ERROR_SCHEMA],
        "detail": detail,
        "status": str(status_code),
    }
    if scim_type:
        body["scimType"] = scim_type
    return body


def is_scim_api_path(path: str, base_path: str = "") -> bool:
    """True for SCIM discovery and resource routes (not /health or /)."""
    path = path.split("?", 1)[0]
    base = (base_path or "").rstrip("/")
    if base and path.startswith(base):
        path = path[len(base):] or "/"
    if path in ("/", ""):
        return False
    if path == "/health":
        return False
    if path.startswith("/docs") or path.endswith("/openapi.json"):
        return False
    scim_prefixes = (
        "/Users",
        "/Groups",
        "/Schemas",
        "/ResourceTypes",
        "/ServiceProviderConfig",
        "/Bulk",
        "/Events",
        "/Async",
    )
    return any(
        path == prefix or path.startswith(f"{prefix}/")
        for prefix in scim_prefixes
    )


def scim_error_response(
    status_code: int,
    detail: Union[str, Any],
    *,
    scim_type: Optional[str] = None,
) -> JSONResponse:
    if isinstance(detail, dict) and detail.get("schemas") == [SCIM_ERROR_SCHEMA]:
        body = detail
    else:
        body = build_scim_error(
            status_code,
            str(detail),
            scim_type=scim_type,
        )
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type=SCIM_CONTENT_TYPE,
    )


def register_scim_exception_handlers(app: FastAPI, base_path: str = "") -> None:
    """Register handlers so SCIM routes return Error resources, not FastAPI JSON."""

    @app.exception_handler(HTTPException)
    async def scim_http_exception_handler(
        request: Request,
        exc: HTTPException,
    ):
        if is_scim_api_path(request.url.path, base_path):
            scim_type = None
            if exc.status_code == 401:
                scim_type = "invalidCredentials"
            elif exc.status_code == 404:
                scim_type = "invalidPath"
            elif exc.status_code == 409:
                scim_type = "uniqueness"
            elif exc.status_code == 412:
                scim_type = "mutability"
            return scim_error_response(
                exc.status_code,
                exc.detail,
                scim_type=scim_type,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(StarletteHTTPException)
    async def scim_starlette_http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ):
        if is_scim_api_path(request.url.path, base_path):
            return scim_error_response(
                exc.status_code,
                exc.detail,
                scim_type="invalidPath" if exc.status_code == 404 else None,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def scim_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        if is_scim_api_path(request.url.path, base_path):
            errors = exc.errors()
            detail = "; ".join(
                f"{'.'.join(str(p) for p in e.get('loc', []))}: {e.get('msg')}"
                for e in errors
            )
            return scim_error_response(
                400,
                detail or "Invalid SCIM request",
                scim_type="invalidSyntax",
            )
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )
