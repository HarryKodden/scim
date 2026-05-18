# routers/feeds.py

"""Event feed discovery and RFC 8936 poll stream (RFC 9967 §2.3)."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import api_key_auth
from events.config import load_event_config
from events.delivery.poll import poll_enabled, poll_feed
from events.feed_registry import get_feed as get_feed_definition
from events.feed_registry import get_members, list_feeds_metadata
from routers import BASE_PATH, SCIM_Route, SCIM_Response

router = APIRouter(
    prefix=BASE_PATH + "/Events/Feeds",
    tags=["SCIM Event Feeds"],
    route_class=SCIM_Route,
    dependencies=[Depends(api_key_auth)],
)


@router.get("", response_class=SCIM_Response)
async def list_feeds() -> Any:
    """List configured event feeds."""
    cfg = load_event_config()
    feeds = list_feeds_metadata(issuer=cfg.issuer, base_path=BASE_PATH)
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(feeds),
        "itemsPerPage": len(feeds),
        "startIndex": 1,
        "Resources": feeds,
    }


@router.get("/{feed_id}", response_class=SCIM_Response)
async def get_feed_resource(feed_id: str) -> Any:
    """Feed metadata and current member resource URIs."""
    feed = get_feed_definition(feed_id)
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed not found: {feed_id}",
        )
    cfg = load_event_config()
    meta = list_feeds_metadata(issuer=cfg.issuer, base_path=BASE_PATH)
    feed_meta = next((f for f in meta if f["id"] == feed_id), None)
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Feed"],
        "id": feed_id,
        "displayName": feed.display_name,
        "uri": feed_meta["uri"] if feed_meta else feed.relative_uri,
        "members": get_members(feed_id),
        "poll": {
            "supported": poll_enabled(),
            "stream": f"{BASE_PATH}/Events/Feeds/{feed_id}/Stream",
        },
    }


@router.get("/{feed_id}/Stream", response_class=SCIM_Response)
async def poll_feed_stream(
    feed_id: str,
    after: Optional[str] = Query(default=None, description="jti to resume after"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> Any:
    """
    RFC 8936 poll delivery — return SETs from the in-memory stream.
    """
    if not poll_enabled():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Poll delivery is disabled (set SET_POLL_ENABLED=true)",
        )
    if not get_feed_definition(feed_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed not found: {feed_id}",
        )

    sets, more = poll_feed(feed_id, after_jti=after, limit=limit)
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:FeedStream"],
        "feed": feed_id,
        "sets": sets,
        "moreAvailable": more,
    }
