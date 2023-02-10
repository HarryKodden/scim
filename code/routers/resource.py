# routers/schema.py

from fastapi import APIRouter, HTTPException

from typing import Any
from schema import ListResponse, resourceTypes

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ResourceTypes",
    tags=["SCIM Resource Types"],
)


@router.get("")
async def get_resource_types() -> ListResponse:
    """ Return Resource Types """

    resources = []

    for r in resourceTypes:
        logger.debug(r)
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


@router.get("/{id}")
async def get_resource(id: str) -> Any:
    """ Return Resource Type """

    for resource in resourceTypes:
        if resource.id == id:
            return resource.dict(by_alias=True)

    raise HTTPException(status_code=404, detail=f"Resource {id} not found")
