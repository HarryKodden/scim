# services/users.py

"""User resource mutations (shared by REST routers and bulk)."""

import json
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException
from pydantic import ValidationError
from pydantic_core import from_json

from schema import GroupResource, Patch, User, SCIM_PATCH_OP
from data.users import get_user_resource, put_user_resource, del_user_resource
from data.groups import get_group_resources, remove_member
from filter import Filter
from routers import BASE_PATH, resource_exists, patch_resource
from events.publisher import emit_group_event, emit_user_event, emit_user_lifecycle_event
from versioning import detect_active_change, dump_resource, etag_matches, resource_version


def _scim_error(status_code: int, detail: str) -> Dict[str, Any]:
    from schema import SCIM_API_MESSAGES
    return {
        "schemas": [SCIM_API_MESSAGES + ":Error"],
        "detail": detail,
        "status": str(status_code),
    }


def create_user(
    user_data: Dict[str, Any],
    *,
    emit_events: bool = True,
) -> Tuple[int, Dict[str, Any], Optional[str]]:
    try:
        user = User(**user_data)
    except ValidationError as exc:
        return 422, _scim_error(422, f"Invalid User resource: {exc}"), None

    if resource_exists("User", f'userName eq "{user.userName}"'):
        return 409, _scim_error(409, "userName already exists"), None

    if user.externalId and resource_exists(
        "User", f'externalId eq "{user.externalId}"'
    ):
        return 409, _scim_error(409, "User already exists with same externalId"), None

    try:
        resource = put_user_resource(None, user)
        if emit_events:
            emit_user_event("create", resource, base_path=BASE_PATH)
        body = dump_resource(resource)
        location = body.get("meta", {}).get("location")
        return 201, body, location
    except Exception as exc:
        return 404, _scim_error(404, f"Error: {exc}"), None


def update_user(
    user_id: str,
    user_data: Dict[str, Any],
    *,
    if_match: Optional[str] = None,
    emit_events: bool = True,
) -> Tuple[int, Dict[str, Any], Optional[str]]:
    existing = get_user_resource(user_id)
    if not existing:
        return 404, _scim_error(404, f"User {user_id} not found"), None

    if not etag_matches(if_match, resource_version(existing)):
        return 412, _scim_error(412, "Resource version mismatch (If-Match)"), None

    try:
        user = User(**user_data)
    except ValidationError as exc:
        return 422, _scim_error(422, f"Invalid User resource: {exc}"), None

    if resource_exists("User", f'userName eq "{user.userName}" and id ne "{user_id}"'):
        return 409, _scim_error(409, "userName already exists"), None

    if user.externalId and resource_exists(
        "User", f'externalId eq "{user.externalId}" and id ne "{user_id}"'
    ):
        return 409, _scim_error(409, "User already exists with same externalId"), None

    try:
        resource = put_user_resource(user_id, user)
        if not resource:
            return 404, _scim_error(404, f"User {user_id} not found"), None
        if emit_events:
            emit_user_event("put", resource, base_path=BASE_PATH)
            lifecycle = detect_active_change(existing, resource)
            if lifecycle:
                emit_user_lifecycle_event(lifecycle, resource, base_path=BASE_PATH)
        body = dump_resource(resource)
        return 200, body, body.get("meta", {}).get("location")
    except Exception as exc:
        return 404, _scim_error(404, f"Error: {exc}"), None


def patch_user(
    user_id: str,
    patch_data: Dict[str, Any],
    *,
    if_match: Optional[str] = None,
    emit_events: bool = True,
) -> Tuple[int, Dict[str, Any], Optional[str]]:
    user = get_user_resource(user_id)
    if not user:
        return 404, _scim_error(404, f"User {user_id} not found"), None

    if not etag_matches(if_match, resource_version(user)):
        return 412, _scim_error(412, "Resource version mismatch (If-Match)"), None

    try:
        patch = Patch(**patch_data)
    except ValidationError as exc:
        return 400, _scim_error(400, f"Invalid PatchOp: {exc}"), None

    if SCIM_PATCH_OP not in patch.schemas:
        return 400, _scim_error(400, f"Missing schema {SCIM_PATCH_OP}"), None

    try:
        before = get_user_resource(user_id)
        resource = patch_resource(
            user.model_dump(by_alias=True, exclude_none=True),
            patch.Operations,
        )
        updated = put_user_resource(user_id, User(**resource))
        if emit_events:
            emit_user_event(
                "patch",
                updated,
                patch_operations=patch.Operations,
                base_path=BASE_PATH,
            )
            lifecycle = detect_active_change(before, updated)
            if lifecycle:
                emit_user_lifecycle_event(lifecycle, updated, base_path=BASE_PATH)
        body = dump_resource(updated)
        return 200, body, body.get("meta", {}).get("location")
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return exc.status_code, _scim_error(exc.status_code, detail), None
    except Exception as exc:
        return 400, _scim_error(400, f"Error: {exc}"), None


def delete_user(
    user_id: str,
    *,
    emit_events: bool = True,
) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
    resource = get_user_resource(user_id)
    if not resource:
        return 404, _scim_error(404, f"User {user_id} not found"), None

    if emit_events:
        groups = get_group_resources(Filter(f'members[value eq "{user_id}"]'))
        for g in groups:
            group = GroupResource.model_validate(from_json(json.dumps(g)))
            if remove_member(group, user_id):
                emit_group_event("patch", group, base_path=BASE_PATH)
        emit_user_event("delete", resource, base_path=BASE_PATH)

    del_user_resource(user_id)
    return 204, None, None
