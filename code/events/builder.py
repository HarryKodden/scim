# events/builder.py

"""SET construction (RFC 8417 / RFC 9967)."""

import os
import time
import uuid
from typing import Any, Dict, List, Literal, Optional

from events.config import EventConfig, load_event_config
from events.mapping import (
    PROV_CREATE_FULL,
    PROV_CREATE_NOTICE,
    PROV_DELETE,
    PROV_PATCH_FULL,
    PROV_PATCH_NOTICE,
    PROV_PUT_FULL,
    PROV_PUT_NOTICE,
)

ProvisioningOp = Literal["create", "put", "patch", "delete"]

_NOTICE_URI = {
    "create": PROV_CREATE_NOTICE,
    "put": PROV_PUT_NOTICE,
    "patch": PROV_PATCH_NOTICE,
    "delete": PROV_DELETE,
}

_FULL_URI = {
    "create": PROV_CREATE_FULL,
    "put": PROV_PUT_FULL,
    "patch": PROV_PATCH_FULL,
    "delete": PROV_DELETE,
}


def new_jti() -> str:
    return str(uuid.uuid4())


def new_txn() -> str:
    return str(uuid.uuid4())


def build_sub_id(
    resource_uri: str,
    external_id: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> Dict[str, Any]:
    """RFC 9967 §2.1 — subject identification via sub_id (not sub)."""
    sub_id: Dict[str, Any] = {
        "format": "scim",
        "uri": resource_uri,
    }
    if external_id is not None:
        sub_id["externalId"] = external_id
    if resource_id is not None:
        sub_id["id"] = resource_id
    return sub_id


def resource_relative_uri(
    resource: Dict[str, Any],
    resource_type: str,
    base_path: Optional[str] = None,
) -> str:
    """SCIM relative URI for sub_id.uri (after service provider base path)."""
    base_path = base_path if base_path is not None else os.environ.get("BASE_PATH", "")
    meta = resource.get("meta") or {}
    location = meta.get("location")
    if isinstance(location, str) and location:
        if base_path and base_path not in ("", "/"):
            bp = base_path.rstrip("/")
            if location == bp or location.startswith(f"{bp}/"):
                return location[len(bp):] or location
        return location

    resource_id = resource.get("id", "")
    path = f"/{resource_type}s/{resource_id}"
    return path


def attributes_from_patch_operations(operations: Any) -> List[str]:
    paths: List[str] = []
    for operation in operations or []:
        path = getattr(operation, "path", None) or (
            operation.get("path") if isinstance(operation, dict) else None
        )
        if path and path not in paths:
            paths.append(path)
    return paths


def attributes_from_resource(resource: Dict[str, Any]) -> List[str]:
    skip = {"schemas", "meta"}
    return sorted(k for k in resource.keys() if k not in skip)


def build_event_payload(
    operation: ProvisioningOp,
    resource: Dict[str, Any],
    attributes: Optional[List[str]],
    config: EventConfig,
    patch_operations: Any = None,
) -> Dict[str, Any]:
    if operation == "delete":
        return {}

    if config.event_mode == "full":
        if operation == "patch" and patch_operations is not None:
            ops = []
            for op in patch_operations:
                if hasattr(op, "model_dump"):
                    ops.append(op.model_dump(by_alias=True, exclude_none=True))
                elif isinstance(op, dict):
                    ops.append(op)
                else:
                    ops.append({
                        "op": getattr(op, "op", None),
                        "path": getattr(op, "path", None),
                        "value": getattr(op, "value", None),
                    })
            return {
                "data": {
                    "schemas": resource.get(
                        "schemas",
                        ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    ),
                    "Operations": ops,
                }
            }
        payload: Dict[str, Any] = {"data": dict(resource)}
        return payload

    attrs = attributes
    if attrs is None:
        if operation == "patch":
            attrs = attributes_from_patch_operations(patch_operations)
        else:
            attrs = attributes_from_resource(resource)
    return {"attributes": attrs}


def build_set_envelope(
    event_uri: str,
    event_payload: Dict[str, Any],
    sub_id: Dict[str, Any],
    config: Optional[EventConfig] = None,
    txn: Optional[str] = None,
    audience: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Assemble top-level SET claims. Signing deferred to Phase 3."""
    cfg = config or load_event_config()

    aud = audience
    if aud is None and cfg.audience:
        aud = [cfg.audience]

    envelope: Dict[str, Any] = {
        "iss": cfg.issuer,
        "iat": int(time.time()),
        "jti": new_jti(),
        "sub_id": sub_id,
        "events": {
            event_uri: event_payload,
        },
    }
    if aud:
        envelope["aud"] = aud
    if txn:
        envelope["txn"] = txn
    return envelope


def build_provisioning_event(
    operation: ProvisioningOp,
    resource_type: str,
    resource: Dict[str, Any],
    attributes: Optional[List[str]] = None,
    config: Optional[EventConfig] = None,
    patch_operations: Any = None,
    base_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a complete provisioning SET for one resource change."""
    cfg = config or load_event_config()
    uri_map = _FULL_URI if cfg.event_mode == "full" else _NOTICE_URI
    event_uri = uri_map[operation]

    rel_uri = resource_relative_uri(resource, resource_type, base_path)
    sub_id = build_sub_id(
        rel_uri,
        external_id=resource.get("externalId"),
        resource_id=resource.get("id"),
    )
    payload = build_event_payload(
        operation,
        resource,
        attributes,
        cfg,
        patch_operations=patch_operations,
    )
    return build_set_envelope(event_uri, payload, sub_id, config=cfg)
