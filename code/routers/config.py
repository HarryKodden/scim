# routers/provider.py

import json

from typing import Any
from fastapi import APIRouter, HTTPException
from schema import ListResponse, Schemas

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
      "documentationUri": "https://github.com/HarryKodden/scim-sample",
      "authenticationSchemes": [
        {
          "name": "OAuth Bearer Token",
          "description": "Authentication scheme using the OAuth Bearer Token Standard",
          "specUri": "http://www.rfc-editor.org/info/rfc6750",
          "type": "oauthbearertoken",
          "primary": False
        },
        {
          "name": "APIKey Header",
          "description": "Authentication scheme using the APIKey Header",
          "specUri": "???",
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
