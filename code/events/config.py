# events/config.py

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EventConfig:
    """RFC 9967 / SET delivery configuration from environment."""

    issuer: str
    audience: Optional[str]
    push_url: Optional[str]
    push_token: Optional[str]
    event_mode: str
    async_request: str

    @property
    def push_enabled(self) -> bool:
        return bool(self.push_url)


def load_event_config() -> EventConfig:
    event_mode = os.environ.get("EVENT_MODE", "notice").lower()
    if event_mode not in {"notice", "full"}:
        event_mode = "notice"

    async_request = os.environ.get("ASYNC_REQUEST", "none").lower()
    if async_request not in {"none", "long", "request"}:
        async_request = "none"

    return EventConfig(
        issuer=os.environ.get("SET_ISSUER", "scim"),
        audience=os.environ.get("SET_AUDIENCE"),
        push_url=os.environ.get("SET_PUSH_URL"),
        push_token=os.environ.get("SET_PUSH_TOKEN"),
        event_mode=event_mode,
        async_request=async_request,
    )
