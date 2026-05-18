# events/__init__.py

"""
RFC 9967 Security Event Token publishing.
"""

import logging
from typing import Any, Dict

from events.config import EventConfig, load_event_config
from events.delivery.dispatch import deliver_set
from events.feed_registry import list_feeds_metadata
from events.mapping import (
    DEFAULT_NOTICE_EVENT_URIS,
    FEED_ADD,
    FEED_REMOVE,
    MISC_ASYNC_RESP,
    PROV_ACTIVATE,
    PROV_CREATE_FULL,
    PROV_DEACTIVATE,
    PROV_PATCH_FULL,
    PROV_PUT_FULL,
    PROV_DELETE,
)
from events.publisher import emit_group_event, emit_user_event, publish_provisioning_event

logger = logging.getLogger(__name__)

__all__ = [
    "publish_event",
    "publish_provisioning_event",
    "emit_user_event",
    "emit_group_event",
    "load_event_config",
    "EventConfig",
    "DEFAULT_NOTICE_EVENT_URIS",
    "security_events_config",
]


def security_events_config(config: EventConfig = None) -> Dict[str, Any]:
    """ServiceProviderConfig.securityEvents block (RFC 9967 §4)."""
    cfg = config or load_event_config()
    if cfg.event_mode == "full":
        event_uris = [
            PROV_CREATE_FULL,
            PROV_PATCH_FULL,
            PROV_PUT_FULL,
            PROV_DELETE,
        ]
    else:
        event_uris = list(DEFAULT_NOTICE_EVENT_URIS)

    for uri in (PROV_ACTIVATE, PROV_DEACTIVATE):
        if uri not in event_uris:
            event_uris.append(uri)

    if cfg.async_request in ("request", "long"):
        if MISC_ASYNC_RESP not in event_uris:
            event_uris.append(MISC_ASYNC_RESP)

    feeds_meta = list_feeds_metadata(issuer=cfg.issuer)
    for uri in (FEED_ADD, FEED_REMOVE):
        if uri not in event_uris:
            event_uris.append(uri)

    result = {
        "asyncRequest": cfg.async_request,
        "eventUris": event_uris,
        "feeds": [f["uri"] for f in feeds_meta],
    }
    return result


def publish_event(set_token: Dict[str, Any], config: EventConfig = None) -> bool:
    """
    Deliver a Security Event Token to configured receivers.

    Does not raise on delivery failure — logs and returns False instead.
    """
    cfg = config or load_event_config()

    if not cfg.push_enabled:
        logger.debug(
            "SET push skipped (SET_PUSH_URL not set); jti=%s",
            set_token.get("jti"),
        )
        return False

    return deliver_set(set_token, cfg)
