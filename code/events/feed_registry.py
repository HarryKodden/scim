# events/feed_registry.py

"""SCIM event feed registry and membership (RFC 9967 §2.3)."""

import json
import os
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

_lock = threading.Lock()
_membership: Dict[str, Set[str]] = {}


@dataclass(frozen=True)
class FeedDefinition:
    id: str
    display_name: str

    @property
    def relative_uri(self) -> str:
        return f"/Events/Feeds/{self.id}"


def _default_feeds() -> List[FeedDefinition]:
    return [FeedDefinition(id="default", display_name="Default event feed")]


def load_feed_definitions() -> List[FeedDefinition]:
    raw = os.environ.get("SET_FEEDS", "").strip()
    if not raw:
        return _default_feeds()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        ids = [part.strip() for part in raw.split(",") if part.strip()]
        return [
            FeedDefinition(id=feed_id, display_name=feed_id)
            for feed_id in ids
        ] or _default_feeds()
    if not isinstance(parsed, list):
        return _default_feeds()
    feeds: List[FeedDefinition] = []
    for item in parsed:
        if isinstance(item, str):
            feeds.append(FeedDefinition(id=item, display_name=item))
        elif isinstance(item, dict) and item.get("id"):
            feeds.append(
                FeedDefinition(
                    id=str(item["id"]),
                    display_name=str(item.get("displayName", item["id"])),
                )
            )
    return feeds or _default_feeds()


def get_feed(feed_id: str) -> Optional[FeedDefinition]:
    for feed in load_feed_definitions():
        if feed.id == feed_id:
            return feed
    if os.environ.get("SET_GROUP_AS_FEED", "true").lower() in ("1", "true", "yes"):
        return FeedDefinition(id=feed_id, display_name=f"Group feed {feed_id}")
    return None


def feed_absolute_uri(
    feed_id: str,
    *,
    issuer: Optional[str] = None,
    base_path: Optional[str] = None,
) -> str:
    """Absolute feed URI for SET aud claim (RFC 9967 Figure 2)."""
    issuer = (issuer or os.environ.get("SET_ISSUER", "scim")).rstrip("/")
    base_path = (base_path if base_path is not None else os.environ.get("BASE_PATH", "")).rstrip("/")
    rel = f"/Events/Feeds/{feed_id}"
    if issuer.startswith("http://") or issuer.startswith("https://"):
        return f"{issuer}{base_path}{rel}"
    return f"{issuer}{base_path}{rel}"


def group_feed_id(group_id: str) -> str:
    """When SET_GROUP_AS_FEED is enabled, each Group maps to a feed."""
    return group_id


def resolve_feed_for_group(group_id: str) -> str:
    if os.environ.get("SET_GROUP_AS_FEED", "true").lower() in ("1", "true", "yes"):
        if get_feed(group_id):
            return group_id
        return group_id
    return "default"


def ensure_feed_exists(feed_id: str) -> FeedDefinition:
    existing = get_feed(feed_id)
    if existing:
        return existing
    dynamic = FeedDefinition(id=feed_id, display_name=f"Group feed {feed_id}")
    with _lock:
        _membership.setdefault(feed_id, set())
    return dynamic


def list_feeds_metadata(
    *,
    issuer: Optional[str] = None,
    base_path: Optional[str] = None,
) -> List[Dict[str, str]]:
    result = []
    for feed in load_feed_definitions():
        result.append({
            "id": feed.id,
            "displayName": feed.display_name,
            "uri": feed_absolute_uri(feed.id, issuer=issuer, base_path=base_path),
            "relativeUri": feed.relative_uri,
        })
    return result


def add_member(feed_id: str, resource_uri: str) -> bool:
    """Add resource to feed; returns True if newly added."""
    ensure_feed_exists(feed_id)
    with _lock:
        members = _membership.setdefault(feed_id, set())
        if resource_uri in members:
            return False
        members.add(resource_uri)
        return True


def remove_member(feed_id: str, resource_uri: str) -> bool:
    """Remove resource from feed; returns True if was present."""
    with _lock:
        members = _membership.get(feed_id)
        if not members or resource_uri not in members:
            return False
        members.remove(resource_uri)
        return True


def get_members(feed_id: str) -> List[str]:
    with _lock:
        return sorted(_membership.get(feed_id, set()))


def clear_feed_registry() -> None:
    """Test helper."""
    with _lock:
        _membership.clear()
