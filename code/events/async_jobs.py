# events/async_jobs.py

"""Async SCIM request handling (RFC 9967 §2.5.1, §3)."""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, Response
from starlette.responses import Response as StarletteResponse

from events.builder import build_set_envelope, build_sub_id, new_txn
from events.config import load_event_config
from events.delivery.push import deliver_set_push
from events.mapping import MISC_ASYNC_RESP
from schema import SCIM_API_MESSAGES

logger = logging.getLogger(__name__)

SET_TXN_HEADER = "Set-Txn"
PREFERENCE_APPLIED_HEADER = "Preference-Applied"
PREFERENCE_APPLIED_VALUE = "respond-async"

# In-memory store (replace with Redis/DB for multi-worker deployments)
_async_results: Dict[str, Dict[str, Any]] = {}
_async_lock = asyncio.Lock()


@dataclass
class AsyncJobRecord:
    txn: str
    method: str
    path: str
    status: str = ""
    location: Optional[str] = None
    version: Optional[str] = None
    response_body: Optional[Any] = None
    error_response: Optional[Dict[str, Any]] = None
    completed: bool = False


def async_result_location(txn: str, base_path: Optional[str] = None) -> str:
    base = (base_path if base_path is not None else os.environ.get("BASE_PATH", "")).rstrip("/")
    if base:
        return f"{base}/Async/{txn}"
    return f"/Async/{txn}"


def _resource_uri_from_request(request: Request) -> str:
    path = request.url.path
    base = os.environ.get("BASE_PATH", "").rstrip("/")
    if base and path.startswith(base):
        return path[len(base):] or path
    return path


def _operation_result(record: AsyncJobRecord) -> Dict[str, Any]:
    op: Dict[str, Any] = {
        "method": record.method,
        "status": record.status,
    }
    if record.location:
        op["location"] = record.location
    if record.version:
        op["version"] = record.version
    if record.error_response:
        op["response"] = record.error_response
    elif record.response_body is not None and record.status not in ("204",):
        op["response"] = record.response_body
    return op


async def store_async_result(record: AsyncJobRecord) -> None:
    async with _async_lock:
        _async_results[record.txn] = _operation_result(record)


async def get_async_result(txn: str) -> Optional[Dict[str, Any]]:
    async with _async_lock:
        return _async_results.get(txn)


def clear_async_results() -> None:
    """Test helper — reset in-memory async result store."""
    _async_results.clear()


def build_async_response_set(
    record: AsyncJobRecord,
    txn: str,
) -> Dict[str, Any]:
    payload = _operation_result(record)
    sub_id = build_sub_id(_resource_uri_from_request_path(record.path))
    envelope = build_set_envelope(
        MISC_ASYNC_RESP,
        payload,
        sub_id,
        txn=txn,
    )
    return envelope


def _resource_uri_from_request_path(path: str) -> str:
    base = os.environ.get("BASE_PATH", "").rstrip("/")
    if base and path.startswith(base):
        return path[len(base):] or path
    return path


def _response_body_from_response(response: Response) -> Optional[Any]:
    if response.status_code == 204:
        return None
    body = getattr(response, "body", None)
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return None


def _error_from_exception(exc: HTTPException) -> Dict[str, Any]:
    detail = exc.detail
    if isinstance(detail, dict):
        return detail
    return {
        "schemas": [SCIM_API_MESSAGES + ":Error"],
        "detail": str(detail),
        "status": str(exc.status_code),
    }


async def _execute_async_job(
    request: Request,
    handler,
    txn: str,
) -> None:
    record = AsyncJobRecord(
        txn=txn,
        method=request.method,
        path=str(request.url.path),
    )
    try:
        response: Response = await handler(request)
        record.status = str(response.status_code)
        record.location = response.headers.get("location")
        record.version = response.headers.get("etag")
        record.response_body = _response_body_from_response(response)
        record.completed = True
        await store_async_result(record)
    except HTTPException as exc:
        record.status = str(exc.status_code)
        record.error_response = _error_from_exception(exc)
        record.completed = True
        await store_async_result(record)
    except Exception as exc:
        logger.exception("Async SCIM job failed: txn=%s error=%s", txn, str(exc))
        record.status = "500"
        record.error_response = {
            "schemas": [SCIM_API_MESSAGES + ":Error"],
            "detail": str(exc),
            "status": "500",
        }
        record.completed = True
        await store_async_result(record)

    try:
        set_token = build_async_response_set(record, txn)
        cfg = load_event_config()
        deliver_set_push(set_token, cfg)
    except Exception as exc:
        logger.error("Failed to publish asyncresp SET: txn=%s error=%s", txn, str(exc))


def _inline_async_enabled() -> bool:
    return os.environ.get("ASYNC_INLINE", "").lower() in ("1", "true", "yes")


async def schedule_async_request(
    request: Request,
    handler,
    txn: str,
) -> None:
    """Run SCIM mutation in background and publish misc:asyncresp when done."""
    if _inline_async_enabled():
        await _execute_async_job(request, handler, txn)
        return
    asyncio.create_task(_execute_async_job(request, handler, txn))


async def accept_async_response(
    request: Request,
    handler,
    txn: Optional[str] = None,
) -> Response:
    """Build 202 Accepted with RFC 9967 required headers."""
    txn = txn or new_txn()
    location = async_result_location(txn)
    if _inline_async_enabled():
        await _execute_async_job(request, handler, txn)
    else:
        asyncio.create_task(_execute_async_job(request, handler, txn))
    return StarletteResponse(
        status_code=202,
        headers={
            SET_TXN_HEADER: txn,
            PREFERENCE_APPLIED_HEADER: PREFERENCE_APPLIED_VALUE,
            "Location": location,
        },
    )
