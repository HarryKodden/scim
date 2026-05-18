# versioning.py

"""Resource versioning and ETag handling (RFC 7644 §3.14)."""

import uuid
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, Response


def new_version() -> str:
    return f'W/"{uuid.uuid4()}"'


def bump_resource_meta(resource: Any) -> str:
    """Assign a new meta.version / meta.etag on a resource model or dict."""
    version = new_version()
    if hasattr(resource, "meta"):
        resource.meta.version = version
        resource.meta.etag = version
    elif isinstance(resource, dict):
        meta = resource.setdefault("meta", {})
        meta["version"] = version
        meta["etag"] = version
    return version


def resource_version(resource: Any) -> Optional[str]:
    if resource is None:
        return None
    if hasattr(resource, "meta"):
        return resource.meta.version or resource.meta.etag
    if isinstance(resource, dict):
        meta = resource.get("meta") or {}
        return meta.get("version") or meta.get("etag")
    return None


def _normalize_etag(value: str) -> str:
    value = value.strip()
    if value.startswith("W/"):
        return value
    if value.startswith('"') and value.endswith('"'):
        return f"W/{value}"
    return value


def etag_matches(if_match: Optional[str], current_version: Optional[str]) -> bool:
    if not if_match or not current_version:
        return True
    candidate = if_match.strip()
    if candidate == "*":
        return True
    return _normalize_etag(candidate) == _normalize_etag(current_version)


def check_if_match(request: Request, current_version: Optional[str]) -> None:
    """Reject PUT/PATCH when If-Match does not match the current version."""
    if not current_version:
        return
    if_match = request.headers.get("if-match")
    if not if_match:
        return
    if not etag_matches(if_match, current_version):
        raise HTTPException(
            status_code=412,
            detail="Resource version mismatch (If-Match)",
        )


def set_etag_header(response: Response, version: Optional[str]) -> None:
    if version:
        response.headers["ETag"] = version


def dump_resource(resource: Any, response: Optional[Response] = None) -> Dict[str, Any]:
    data = resource.model_dump(by_alias=True, exclude_none=True)
    if response is not None:
        set_etag_header(response, (data.get("meta") or {}).get("version"))
    return data


def active_value(resource: Any) -> bool:
    if resource is None:
        return True
    active = getattr(resource, "active", None)
    if active is None and isinstance(resource, dict):
        active = resource.get("active")
    return True if active is None else bool(active)


def detect_active_change(
    before: Any,
    after: Any,
) -> Optional[str]:
    """
    Return 'activate' or 'deactivate' when User.active changes on update.
    Returns None when unchanged or on create.
    """
    if before is None:
        return None
    before_active = active_value(before)
    after_active = active_value(after)
    if before_active == after_active:
        return None
    return "activate" if after_active else "deactivate"
