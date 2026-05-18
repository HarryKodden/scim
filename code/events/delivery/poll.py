# events/delivery/poll.py

"""RFC 8936 poll-based SET delivery (in-memory stream per feed)."""

import os
import threading
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

_lock = threading.Lock()
_streams: Dict[str, Deque[Dict[str, Any]]] = {}


def _max_events() -> int:
    try:
        return max(100, int(os.environ.get("SET_POLL_MAX_EVENTS", "10000")))
    except ValueError:
        return 10000


def poll_enabled() -> bool:
    return os.environ.get("SET_POLL_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )


def append_set_to_feed(feed_id: str, set_token: Dict[str, Any]) -> None:
    if not poll_enabled():
        return
    entry = {
        "jti": set_token.get("jti"),
        "iat": set_token.get("iat"),
        "set": set_token,
    }
    with _lock:
        stream = _streams.setdefault(feed_id, deque(maxlen=_max_events()))
        stream.append(entry)


def _feed_ids_from_aud(set_token: Dict[str, Any]) -> List[str]:
    from events.feed_registry import load_feed_definitions

    aud = set_token.get("aud")
    if aud is None:
        return ["default"]
    if isinstance(aud, str):
        aud_list = [aud]
    else:
        aud_list = list(aud)

    feed_ids: List[str] = []
    for uri in aud_list:
        marker = "/Events/Feeds/"
        if marker in uri:
            feed_ids.append(uri.split(marker, 1)[1].split("/")[0].split("?")[0])
    if feed_ids:
        return feed_ids

    known = {f.id for f in load_feed_definitions()}
    return ["default"] if "default" in known else [load_feed_definitions()[0].id]


def store_set_for_poll(set_token: Dict[str, Any]) -> None:
    """Append SET to poll stream(s) derived from aud or default feed."""
    if not poll_enabled():
        return
    for feed_id in _feed_ids_from_aud(set_token):
        append_set_to_feed(feed_id, set_token)


def poll_feed(
    feed_id: str,
    *,
    after_jti: Optional[str] = None,
    limit: int = 100,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Return SET entries after after_jti (exclusive), up to limit.
    Second value is moreAvailable hint.
    """
    limit = max(1, min(limit, 1000))
    with _lock:
        stream = list(_streams.get(feed_id, deque()))

    if after_jti:
        start = 0
        for idx, entry in enumerate(stream):
            if entry.get("jti") == after_jti:
                start = idx + 1
                break
        stream = stream[start:]

    selected = stream[:limit]
    more = len(stream) > limit
    return [entry["set"] for entry in selected], more


def clear_poll_streams() -> None:
    """Test helper."""
    with _lock:
        _streams.clear()
