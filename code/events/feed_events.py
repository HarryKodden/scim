# events/feed_events.py

"""Emit feed:add / feed:remove and sync membership."""

import json
import logging
from typing import Any, Optional, Set

from data.users import get_user_resource
from events.builder import build_feed_event
from events.config import EventConfig, load_event_config
from events.delivery.dispatch import deliver_set
from events.feed_registry import add_member, remove_member, resolve_feed_for_group

logger = logging.getLogger(__name__)


def feeds_enabled() -> bool:
    import os
    return os.environ.get("SET_FEEDS_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )


def _resource_dict(resource: Any) -> dict:
    if isinstance(resource, dict):
        return resource
    return json.loads(resource.model_dump_json(by_alias=True, exclude_none=True))


def publish_feed_event(
    operation: str,
    resource: Any,
    resource_type: str,
    feed_id: str,
    *,
    config: Optional[EventConfig] = None,
    base_path: Optional[str] = None,
) -> bool:
    if not feeds_enabled():
        return False
    cfg = config or load_event_config()
    try:
        resource_data = _resource_dict(resource)
        rel_uri = resource_data.get("meta", {}).get("location")
        if not rel_uri and resource_data.get("id"):
            rel_uri = f"/{resource_type}s/{resource_data['id']}"
        set_token = build_feed_event(
            operation,
            resource_data,
            resource_type,
            feed_id,
            config=cfg,
            base_path=base_path,
        )
        return deliver_set(set_token, cfg)
    except Exception as exc:
        logger.error(
            "Failed to publish feed:%s: feed=%s error=%s",
            operation,
            feed_id,
            str(exc),
        )
        return False


def emit_feed_add(
    resource: Any,
    resource_type: str,
    feed_id: str,
    *,
    base_path: Optional[str] = None,
) -> bool:
    resource_data = _resource_dict(resource)
    rel_uri = resource_data.get("meta", {}).get("location")
    if not rel_uri and resource_data.get("id"):
        rel_uri = f"/{resource_type}s/{resource_data['id']}"
    if not add_member(feed_id, rel_uri):
        return False
    return publish_feed_event("add", resource_data, resource_type, feed_id, base_path=base_path)


def emit_feed_remove(
    resource: Any,
    resource_type: str,
    feed_id: str,
    *,
    base_path: Optional[str] = None,
) -> bool:
    resource_data = _resource_dict(resource)
    rel_uri = resource_data.get("meta", {}).get("location")
    if not rel_uri and resource_data.get("id"):
        rel_uri = f"/{resource_type}s/{resource_data['id']}"
    if not remove_member(feed_id, rel_uri):
        return False
    return publish_feed_event(
        "remove", resource_data, resource_type, feed_id, base_path=base_path
    )


def member_ids(group: Any) -> Set[str]:
    members = group.members if hasattr(group, "members") else group.get("members", [])
    ids: Set[str] = set()
    for member in members or []:
        value = getattr(member, "value", None)
        if value is None and isinstance(member, dict):
            value = member.get("value")
        if value:
            ids.add(str(value))
    return ids


def emit_group_membership_feed_changes(
    group_id: str,
    before: Any,
    after: Any,
    *,
    base_path: Optional[str] = None,
) -> None:
    """Emit feed:add / feed:remove for User members added or removed from a Group."""
    if not feeds_enabled():
        return
    feed_id = resolve_feed_for_group(group_id)
    added = member_ids(after) - member_ids(before)
    removed = member_ids(before) - member_ids(after)

    for user_id in added:
        user = get_user_resource(user_id)
        if user:
            emit_feed_add(user, "User", feed_id, base_path=base_path)

    for user_id in removed:
        user = get_user_resource(user_id)
        if user:
            emit_feed_remove(user, "User", feed_id, base_path=base_path)
        else:
            remove_member(feed_id, f"/Users/{user_id}")


def emit_initial_group_members(
    group_id: str,
    group: Any,
    *,
    base_path: Optional[str] = None,
) -> None:
    if not feeds_enabled():
        return
    feed_id = resolve_feed_for_group(group_id)
    for user_id in member_ids(group):
        user = get_user_resource(user_id)
        if user:
            emit_feed_add(user, "User", feed_id, base_path=base_path)
