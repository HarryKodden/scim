# events/delivery/push.py

"""RFC 8935 push-based SET delivery (HTTP POST to receiver)."""

import json
import logging
import time
from typing import Any, Dict

import httpx

from events.config import EventConfig

logger = logging.getLogger(__name__)

SET_CONTENT_TYPE = "application/secevent+jwt"
MAX_PUSH_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = (0.5, 1.0, 2.0)


def deliver_set_push(
    set_token: Dict[str, Any],
    config: EventConfig,
) -> bool:
    """
    POST a SET to the configured receiver with retries on 5xx / network errors.
    """
    if not config.push_url:
        return False

    headers = {
        "Content-Type": SET_CONTENT_TYPE,
        "Accept": "application/json",
    }
    if config.push_token:
        headers["Authorization"] = f"Bearer {config.push_token}"

    body = json.dumps(set_token)
    last_error = None

    for attempt, backoff in enumerate(RETRY_BACKOFF_SECONDS):
        if attempt > 0:
            time.sleep(backoff)
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    config.push_url,
                    content=body,
                    headers=headers,
                )
            if response.status_code < 400:
                logger.debug(
                    "SET push accepted: url=%s status=%s jti=%s attempt=%s",
                    config.push_url,
                    response.status_code,
                    set_token.get("jti"),
                    attempt + 1,
                )
                return True
            if response.status_code < 500:
                logger.error(
                    "SET push rejected: url=%s status=%s body=%s",
                    config.push_url,
                    response.status_code,
                    response.text[:500],
                )
                return False
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            last_error = str(exc)

        logger.warning(
            "SET push attempt %s failed: url=%s error=%s",
            attempt + 1,
            config.push_url,
            last_error,
        )

    logger.error(
        "SET push failed after %s attempts: url=%s jti=%s last_error=%s",
        MAX_PUSH_ATTEMPTS,
        config.push_url,
        set_token.get("jti"),
        last_error,
    )
    return False
