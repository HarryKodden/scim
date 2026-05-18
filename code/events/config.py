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
    signing_secret: Optional[str]
    signing_algorithm: str
    push_require_tls: bool
    poll_enabled: bool

    @property
    def push_enabled(self) -> bool:
        return bool(self.push_url)

    @property
    def signing_enabled(self) -> bool:
        return bool(self.signing_secret)


def load_event_config() -> EventConfig:
    event_mode = os.environ.get("EVENT_MODE", "notice").lower()
    if event_mode not in {"notice", "full"}:
        event_mode = "notice"

    async_request = os.environ.get("ASYNC_REQUEST", "none").lower()
    if async_request not in {"none", "long", "request"}:
        async_request = "none"

    signing_algorithm = os.environ.get("SET_SIGNING_ALGORITHM", "HS256")
    push_require_tls = os.environ.get(
        "SET_PUSH_REQUIRE_TLS", "false"
    ).lower() in ("1", "true", "yes")

    push_url = os.environ.get("SET_PUSH_URL")
    if push_url and push_require_tls and push_url.lower().startswith("http://"):
        raise ValueError(
            "SET_PUSH_URL must use HTTPS when SET_PUSH_REQUIRE_TLS is enabled"
        )

    return EventConfig(
        issuer=os.environ.get("SET_ISSUER", "scim"),
        audience=os.environ.get("SET_AUDIENCE"),
        push_url=push_url,
        push_token=os.environ.get("SET_PUSH_TOKEN"),
        event_mode=event_mode,
        async_request=async_request,
        signing_secret=os.environ.get("SET_SIGNING_SECRET"),
        signing_algorithm=signing_algorithm,
        push_require_tls=push_require_tls,
        poll_enabled=os.environ.get("SET_POLL_ENABLED", "false").lower()
        in ("1", "true", "yes"),
    )
