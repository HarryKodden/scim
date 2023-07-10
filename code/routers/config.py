# routers/provider.py

from typing import Any
from fastapi import APIRouter

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ServiceProviderConfig",
    tags=["SCIM Config"],
)


@router.get("")
async def get_config() -> Any:
    """ Return Config """

    return {
      "patch": {
        "supported": True
      },
      "filter": {
        "maxResults": 200,
        "supported": True
      },
      "documentationUri": "https://github.com/HarryKodden/scim",
      "authenticationSchemes": [
        {
          "name": "OAuth Bearer Token",
          "description": """
            Authentication scheme
            using the OAuth Bearer Token Standard
          """,
          "specUri": "https://www.rfc-editor.org/info/rfc6750",
          "type": "oauthbearertoken",
          "primary": False
        },
        {
          "name": "APIKey Header",
          "description": "Authentication scheme using the APIKey Header",
          "specUri": "https://www.rfc-editor.org/rfc/rfc7235",
          "type": "apikey",
          "primary": True
        }
      ],
      "schemas": [
        "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
      ],
      "etag": {
        "supported": False
      },
      "sort": {
        "supported": False
      },
      "bulk": {
        "maxPayloadSize": 1048576,
        "maxOperations": 1000,
        "supported": False
      },
      "changePassword": {
        "supported": False
      }
    }
