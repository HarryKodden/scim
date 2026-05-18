# bulk/executor.py

"""RFC 7644 §3.7 bulk request execution."""

import os
import re
from typing import Any, Dict, List, Optional

from schema import SCIM_BULK_RESPONSE
from services import groups as group_ops
from services import users as user_ops
BASE_PATH = os.environ.get("BASE_PATH", "").rstrip("/")
BULK_ID_PATTERN = re.compile(r"bulkId:([^/]+)")

_USER_COLLECTION = re.compile(r"^/Users/?$")
_USER_ITEM = re.compile(r"^/Users/(?P<id>[^/]+)$")
_GROUP_COLLECTION = re.compile(r"^/Groups/?$")
_GROUP_ITEM = re.compile(r"^/Groups/(?P<id>[^/]+)$")


def normalize_bulk_path(path: str) -> str:
    path = (path or "").split("?", 1)[0]
    if not path.startswith("/"):
        path = f"/{path}"
    if BASE_PATH and path.startswith(BASE_PATH):
        path = path[len(BASE_PATH):] or "/"
    return path


def resolve_bulk_id(path: str, bulk_ids: Dict[str, str]) -> str:
    match = BULK_ID_PATTERN.search(path)
    if not match:
        return path
    bulk_id = match.group(1)
    resource_id = bulk_ids.get(bulk_id)
    if not resource_id:
        raise ValueError(f"Unknown bulkId reference: {bulk_id}")
    return BULK_ID_PATTERN.sub(resource_id, path)


def _register_bulk_id(
    bulk_ids: Dict[str, str],
    bulk_id: Optional[str],
    status: int,
    body: Optional[Dict[str, Any]],
) -> None:
    if not bulk_id or status >= 400 or not body:
        return
    resource_id = body.get("id")
    if resource_id:
        bulk_ids[bulk_id] = resource_id


def _operation_response(
    method: str,
    status: int,
    *,
    bulk_id: Optional[str] = None,
    location: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    op: Dict[str, Any] = {
        "method": method.upper(),
        "status": str(status),
    }
    if bulk_id:
        op["bulkId"] = bulk_id
    if location:
        op["location"] = location
    if body:
        version = (body.get("meta") or {}).get("version")
        if version:
            op["version"] = version
        if status == 204:
            pass
        else:
            op["response"] = body
    return op


def execute_single_operation(
    operation: Dict[str, Any],
    bulk_ids: Dict[str, str],
) -> Dict[str, Any]:
    method = (operation.get("method") or "").upper()
    path = normalize_bulk_path(operation.get("path") or "")
    bulk_id = operation.get("bulkId")
    data = operation.get("data")
    if_match = operation.get("version")

    try:
        path = resolve_bulk_id(path, bulk_ids)
    except ValueError as exc:
        return _operation_response(
            method,
            400,
            bulk_id=bulk_id,
            body={
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "detail": str(exc),
                "status": "400",
            },
        )

    if _USER_COLLECTION.match(path):
        if method == "POST":
            status, body, location = user_ops.create_user(data or {})
        else:
            return _operation_response(
                method,
                405,
                bulk_id=bulk_id,
                body={
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "detail": f"Method {method} not allowed on {path}",
                    "status": "405",
                },
            )
    elif match := _USER_ITEM.match(path):
        user_id = match.group("id")
        if method == "PUT":
            status, body, location = user_ops.update_user(
                user_id, data or {}, if_match=if_match
            )
        elif method == "PATCH":
            status, body, location = user_ops.patch_user(
                user_id, data or {}, if_match=if_match
            )
        elif method == "DELETE":
            status, body, location = user_ops.delete_user(user_id)
        else:
            return _operation_response(
                method,
                405,
                bulk_id=bulk_id,
                body={
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "detail": f"Method {method} not allowed on {path}",
                    "status": "405",
                },
            )
    elif _GROUP_COLLECTION.match(path):
        if method == "POST":
            status, body, location = group_ops.create_group(data or {})
        else:
            return _operation_response(
                method,
                405,
                bulk_id=bulk_id,
                body={
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "detail": f"Method {method} not allowed on {path}",
                    "status": "405",
                },
            )
    elif match := _GROUP_ITEM.match(path):
        group_id = match.group("id")
        if method == "PUT":
            status, body, location = group_ops.update_group(
                group_id, data or {}, if_match=if_match
            )
        elif method == "PATCH":
            status, body, location = group_ops.patch_group(
                group_id, data or {}, if_match=if_match
            )
        elif method == "DELETE":
            status, body, location = group_ops.delete_group(group_id)
        else:
            return _operation_response(
                method,
                405,
                bulk_id=bulk_id,
                body={
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "detail": f"Method {method} not allowed on {path}",
                    "status": "405",
                },
            )
    else:
        return _operation_response(
            method,
            404,
            bulk_id=bulk_id,
            body={
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "detail": f"Unknown path: {path}",
                "status": "404",
            },
        )

    _register_bulk_id(bulk_ids, bulk_id, status, body)
    return _operation_response(
        method,
        status,
        bulk_id=bulk_id,
        location=location,
        body=body,
    )


def execute_bulk(
    operations: List[Dict[str, Any]],
    *,
    fail_on_errors: Optional[int] = None,
    max_operations: int = 1000,
) -> Dict[str, Any]:
    if len(operations) > max_operations:
        raise ValueError(
            f"Bulk request exceeds maxOperations ({max_operations})"
        )

    bulk_ids: Dict[str, str] = {}
    results: List[Dict[str, Any]] = []
    error_count = 0

    for operation in operations:
        result = execute_single_operation(operation, bulk_ids)
        results.append(result)
        try:
            status_code = int(result.get("status", "500"))
        except ValueError:
            status_code = 500
        if status_code >= 400:
            error_count += 1
            if fail_on_errors is not None and error_count >= fail_on_errors:
                break

    return {
        "schemas": [SCIM_BULK_RESPONSE],
        "Operations": results,
    }


def is_bulk_operation_error(op_result: Dict[str, Any]) -> bool:
    try:
        return int(op_result.get("status", "500")) >= 400
    except ValueError:
        return True
