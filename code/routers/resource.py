# routers/schema.py

from fastapi import APIRouter

from schema import \
  CORE_SCHEMA_USER, CORE_SCHEMA_GROUP, \
  SRAM_SCHEMA_USER, SRAM_SCHEMA_GROUP, \
  SchemaExtension, ListResponse, Meta, ResourceType
# GroupResource, UserResource

from routers.users import ENDPOINT as ENDPOINT_USER
from routers.users import ENDPOINT as ENDPOINT_GROUP

import logging
logger = logging.getLogger(__name__)

URI = "/ResourceTypes"

router = APIRouter(
    prefix=URI,
    tags=["SCIM Resource Types"],
)

resourceTypes = [
    ResourceType(
        name="User",
        id="User",
        description="Defined resource types for the User schema",
        endpoint=ENDPOINT_USER,
        meta=Meta(
            location=f"{URI}/User",
            resourceType="ResourceType"
        ),
        schemaExtensions=[
            SchemaExtension(
                schema=SRAM_SCHEMA_USER
            )
        ],
        schema=CORE_SCHEMA_USER,
    ),
    ResourceType(
        name="Group",
        id="Group",
        description="Defined resource types for the Group schema",
        endpoint=ENDPOINT_GROUP,
        meta=Meta(
            location=f"{URI}/Group",
            resourceType="ResourceType"
        ),
        schemaExtensions=[
            SchemaExtension(
                schema=SRAM_SCHEMA_GROUP
            )
        ],
        schema=CORE_SCHEMA_GROUP,
    ),
]


@router.get("")
async def get_resource_types() -> ListResponse:
    """ Return Resource Types """

    resources = []

    for r in resourceTypes:
        logger.info(r)
        resources.append(r.dict(by_alias=True))

    return ListResponse(
        Resources=resources,
        itemsPerPage=len(resources),
        schemas=[
            "urn:ietf:params:scim:api:messages:2.0:ListResponse"
        ],
        startIndex=1,
        totalResults=len(resources)
    )
