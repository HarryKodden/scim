# events/__init__.py

"""
RFC 9967 Security Event Token publishing.
"""

import logging
from typing import Any, Dict, List

from events.config import EventConfig, load_event_config
from events.delivery.push import deliver_set_push
from events.mapping import (
    DEFAULT_NOTICE_EVENT_URIS,
    PROV_CREATE_FULL,
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

    return {
        "asyncRequest": cfg.async_request,
        "eventUris": event_uris,
    }


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

    return deliver_set_push(set_token, cfg)
