# events/delivery/dispatch.py

"""Shared SET delivery (push + poll)."""

import logging
import threading
from typing import Any, Dict

from events.config import EventConfig
from events.delivery.poll import store_set_for_poll
from events.delivery.push import deliver_set_push

logger = logging.getLogger(__name__)


def deliver_set(set_token: Dict[str, Any], config: EventConfig) -> bool:
    """
    Push when configured; always append to poll stream when poll is enabled.

    Push runs on a background thread so a synchronous SCIM request that emits a
    SET can still serve JWKS to the receiver while the push is in flight
    (otherwise a single-worker Uvicorn deadlocks: push waits for JWKS, JWKS waits
    for the request to finish).
    """
    stored = False
    if config.poll_enabled:
        store_set_for_poll(set_token)
        stored = True
    if not config.push_enabled:
        return stored

    payload = dict(set_token)

    def _push() -> None:
        try:
            deliver_set_push(payload, config)
        except Exception:
            logger.exception(
                "Background SET push failed: jti=%s", payload.get("jti")
            )

    threading.Thread(target=_push, daemon=True, name="set-push-delivery").start()
    return True
