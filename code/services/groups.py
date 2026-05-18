# services/groups.py

"""Group resource mutations (shared by REST routers and bulk)."""

from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError

from schema import Group, Patch, SCIM_PATCH_OP
from data.groups import get_group_resource, put_group_resource, del_group_resource
from routers import BASE_PATH, resource_exists, patch_resource
from events.feed_events import (
    emit_group_membership_feed_changes,
    emit_initial_group_members,
)
from events.publisher import emit_group_event
from versioning import dump_resource, etag_matches, resource_version


def _scim_error(status_code: int, detail: str) -> Dict[str, Any]:
    from schema import SCIM_API_MESSAGES
    return {
        "schemas": [SCIM_API_MESSAGES + ":Error"],
        "detail": detail,
        "status": str(status_code),
    }


def create_group(
    group_data: Dict[str, Any],
    *,
    emit_events: bool = True,
) -> Tuple[int, Dict[str, Any], Optional[str]]:
    try:
        group = Group(**group_data)
    except ValidationError as exc:
        return 422, _scim_error(422, f"Invalid Group resource: {exc}"), None

    if group.externalId and resource_exists(
        "Group", f'externalId eq "{group.externalId}"'
    ):
        return 409, _scim_error(409, "Group already exists with same externalId"), None

    try:
        resource = put_group_resource(None, group)
        if emit_events:
            emit_group_event("create", resource, base_path=BASE_PATH)
            emit_initial_group_members(resource.id, resource, base_path=BASE_PATH)
        body = dump_resource(resource)
        return 201, body, body.get("meta", {}).get("location")
    except ValidationError:
        return 422, _scim_error(422, "Invalid Group resource"), None
    except Exception as exc:
        return 404, _scim_error(404, f"Error: {exc}"), None


def update_group(
    group_id: str,
    group_data: Dict[str, Any],
    *,
    if_match: Optional[str] = None,
    emit_events: bool = True,
) -> Tuple[int, Dict[str, Any], Optional[str]]:
    existing = get_group_resource(group_id)
    if not existing:
        return 404, _scim_error(404, f"Group {group_id} not found"), None

    if not etag_matches(if_match, resource_version(existing)):
        return 412, _scim_error(412, "Resource version mismatch (If-Match)"), None

    try:
        group = Group(**group_data)
    except ValidationError as exc:
        return 422, _scim_error(422, f"Invalid Group resource: {exc}"), None

    if group.externalId and resource_exists(
        "Group", f'externalId eq "{group.externalId}" and id ne "{group_id}"'
    ):
        return 409, _scim_error(409, "Group already exists with same externalId"), None

    try:
        resource = put_group_resource(group_id, group)
        if not resource:
            return 404, _scim_error(404, f"Group {group_id} not found"), None
        if emit_events:
            emit_group_event("put", resource, base_path=BASE_PATH)
            emit_group_membership_feed_changes(
                group_id, existing, resource, base_path=BASE_PATH
            )
        body = dump_resource(resource)
        return 200, body, body.get("meta", {}).get("location")
    except Exception as exc:
        return 404, _scim_error(404, f"Error: {exc}"), None


def patch_group(
    group_id: str,
    patch_data: Dict[str, Any],
    *,
    if_match: Optional[str] = None,
    emit_events: bool = True,
) -> Tuple[int, Dict[str, Any], Optional[str]]:
    group = get_group_resource(group_id)
    if not group:
        return 404, _scim_error(404, f"Group {group_id} not found"), None

    if not etag_matches(if_match, resource_version(group)):
        return 412, _scim_error(412, "Resource version mismatch (If-Match)"), None

    try:
        patch = Patch(**patch_data)
    except ValidationError as exc:
        return 400, _scim_error(400, f"Invalid PatchOp: {exc}"), None

    if SCIM_PATCH_OP not in patch.schemas:
        return 400, _scim_error(400, f"Missing schema {SCIM_PATCH_OP}"), None

    try:
        before = get_group_resource(group_id)
        resource = patch_resource(
            group.model_dump(by_alias=True, exclude_none=True),
            patch.Operations,
        )
        updated = put_group_resource(group_id, Group(**resource))
        if emit_events:
            emit_group_event(
                "patch",
                updated,
                patch_operations=patch.Operations,
                base_path=BASE_PATH,
            )
            emit_group_membership_feed_changes(
                group_id, before, updated, base_path=BASE_PATH
            )
        body = dump_resource(updated)
        return 200, body, body.get("meta", {}).get("location")
    except Exception as exc:
        return 400, _scim_error(400, f"Error: {exc}"), None


def delete_group(
    group_id: str,
    *,
    emit_events: bool = True,
) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
    resource = get_group_resource(group_id)
    if not resource:
        return 404, _scim_error(404, f"Group {group_id} not found"), None

    if emit_events:
        emit_group_event("delete", resource, base_path=BASE_PATH)
    del_group_resource(group_id)
    return 204, None, None
