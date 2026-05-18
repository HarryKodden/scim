# events/signing.py

"""Optional JWS signing for SET delivery (RFC 8417)."""

import json
from typing import Any, Dict, Tuple

import jwt

from events.config import EventConfig

SET_CONTENT_TYPE = "application/secevent+jwt"
UNSIGNED_SET_CONTENT_TYPE = "application/json"


def prepare_set_delivery_body(
    set_token: Dict[str, Any],
    config: EventConfig,
) -> Tuple[str, str]:
    """
    Serialize a SET for HTTP push.

    Returns (body, content-type). When SET_SIGNING_SECRET is set, body is a
    compact JWS; otherwise the SET is sent as JSON (legacy/dev receivers).
    """
    if config.signing_enabled:
        token = jwt.encode(
            set_token,
            config.signing_secret,
            algorithm=config.signing_algorithm,
        )
        return token, SET_CONTENT_TYPE
    return json.dumps(set_token), UNSIGNED_SET_CONTENT_TYPE
