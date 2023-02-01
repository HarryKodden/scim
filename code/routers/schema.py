# routers/schema.py

import json
from fastapi import APIRouter

from schema import ListResponse, \
  CORE_SCHEMA_USER, UserResource, \
  CORE_SCHEMA_GROUP, GroupResource, \
  SRAM_SCHEMA_USER, SRAM_User_Extension, \
  SRAM_SCHEMA_GROUP, SRAM_Group_Extension

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/Schemas",
    tags=["SCIM Schemas"],
)

schemas = {
    CORE_SCHEMA_USER: UserResource,
    CORE_SCHEMA_GROUP: GroupResource,
    SRAM_SCHEMA_USER: SRAM_User_Extension,
    SRAM_SCHEMA_GROUP: SRAM_Group_Extension,
}


@router.get("")
async def get_group() -> ListResponse:
    """ Return Schemas """

    resources = []

    for schema in schemas.keys():
        resources.append(
            json.loads(schemas[schema].schema_json(by_alias=True))
        )

    return ListResponse(
        Resources=resources,
        itemsPerPage=len(resources),
        schemas=[
            "urn:ietf:params:scim:api:messages:2.0:ListResponse"
        ],
        startIndex=1,
        totalResults=len(resources)
    )
