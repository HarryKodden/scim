# events/delivery/dispatch.py

"""Shared SET delivery (push + poll)."""

from typing import Any, Dict

from events.config import EventConfig
from events.delivery.poll import store_set_for_poll
from events.delivery.push import deliver_set_push


def deliver_set(set_token: Dict[str, Any], config: EventConfig) -> bool:
    """Push when configured; always append to poll stream when poll is enabled."""
    stored = False
    if config.poll_enabled:
        store_set_for_poll(set_token)
        stored = True
    if not config.push_enabled:
        return stored
    return deliver_set_push(set_token, config) or stored
