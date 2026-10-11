# events/signing.py

"""Optional JWS signing for SET delivery (RFC 8417)."""

import json
from typing import Any, Dict, Tuple

import jwt

from events.config import EventConfig

SET_CONTENT_TYPE = "application/secevent+jwt"
UNSIGNED_SET_CONTENT_TYPE = "application/json"
SET_TYPE_HEADER = "secevent+jwt"


def prepare_set_delivery_body(
    set_token: Dict[str, Any],
    config: EventConfig,
) -> Tuple[str, str]:
    """
    Serialize a SET for HTTP push.

    Returns (body, content-type). When RSA or HMAC signing is configured, body is a
    compact JWS with typ secevent+jwt; otherwise the SET is sent as JSON
    (legacy/dev receivers).
    """
    if config.signing_key is not None:
        headers = {
            "typ": SET_TYPE_HEADER,
            "kid": config.signing_key.key_id,
        }
        token = jwt.encode(
            set_token,
            config.signing_key.private_key_pem,
            algorithm=config.signing_key.algorithm,
            headers=headers,
        )
        return token, SET_CONTENT_TYPE

    if config.signing_secret:
        token = jwt.encode(
            set_token,
            config.signing_secret,
            algorithm=config.signing_algorithm,
            headers={"typ": SET_TYPE_HEADER},
        )
        return token, SET_CONTENT_TYPE

    return json.dumps(set_token), UNSIGNED_SET_CONTENT_TYPE
