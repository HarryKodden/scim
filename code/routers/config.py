# routers/config.py

from typing import Any
from fastapi import APIRouter
from routers import BASE_PATH, SCIM_Response
from events import security_events_config
from scim_errors import SCIM_EVENTS_EXTENSION

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=BASE_PATH + "/ServiceProviderConfig",
    tags=["SCIM Config"],
)


@router.get("", response_class=SCIM_Response)
async def get_config() -> Any:
    """Return ServiceProviderConfig (RFC 7643 + RFC 9967 extension)."""
    security_events = security_events_config()
    return {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig",
            SCIM_EVENTS_EXTENSION,
        ],
        "patch": {
            "supported": True,
        },
        "filter": {
            "maxResults": 200,
            "supported": True,
        },
        "documentationUri": "https://github.com/HarryKodden/scim",
        "authenticationSchemes": [
            {
                "name": "OAuth Bearer Token",
                "description": (
                    "Authentication scheme using the OAuth Bearer Token Standard"
                ),
                "specUri": "https://www.rfc-editor.org/info/rfc6750",
                "type": "oauthbearertoken",
                "primary": False,
            },
            {
                "name": "API Key Header",
                "description": (
                    "API key sent in the X-API-Key request header "
                    "(RFC 7643 httpbasic scheme for header-based credentials)"
                ),
                "specUri": "https://www.rfc-editor.org/rfc/rfc7235",
                "type": "httpbasic",
                "primary": True,
            },
        ],
        "etag": {
            "supported": True,
        },
        "sort": {
            "supported": False,
        },
        "bulk": {
            "maxPayloadSize": 1048576,
            "maxOperations": 1000,
            "supported": True,
        },
        "changePassword": {
            "supported": False,
        },
        SCIM_EVENTS_EXTENSION: security_events,
    }
