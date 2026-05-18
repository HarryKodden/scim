# routers/bulk.py

"""RFC 7644 §3.7 Bulk endpoint."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from auth import api_key_auth
from bulk.executor import execute_bulk
from events.async_jobs import accept_bulk_async_response
from events.config import load_event_config
from events.prefer import wants_respond_async
from routers import BASE_PATH, SCIM_Route, SCIM_Response
from schema import SCIM_BULK_REQUEST, BulkRequest

import logging

logger = logging.getLogger(__name__)

BULK_MAX_OPERATIONS = 1000

router = APIRouter(
    prefix=BASE_PATH + "/Bulk",
    tags=["SCIM Bulk"],
    route_class=SCIM_Route,
    dependencies=[Depends(api_key_auth)],
)


@router.post("", response_class=SCIM_Response)
async def post_bulk(request: Request, bulk: BulkRequest) -> Any:
    """Execute a SCIM bulk request (sync or async per RFC 9967 §2.5.1.2)."""
    if SCIM_BULK_REQUEST not in bulk.schemas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing schema {SCIM_BULK_REQUEST}",
        )

    operations = [
        op.model_dump(by_alias=True, exclude_none=True)
        for op in bulk.Operations
    ]
    fail_on_errors = bulk.failOnErrors
    cfg = load_event_config()
    prefer = request.headers.get("prefer", "")
    async_enabled = cfg.async_request in ("request", "long")
    respond_async = wants_respond_async(prefer)

    if async_enabled and cfg.async_request == "request" and respond_async:
        return await accept_bulk_async_response(
            operations,
            fail_on_errors,
            BULK_MAX_OPERATIONS,
        )

    try:
        return execute_bulk(
            operations,
            fail_on_errors=fail_on_errors,
            max_operations=BULK_MAX_OPERATIONS,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
