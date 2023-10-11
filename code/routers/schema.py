# routers/schema.py

from fastapi import APIRouter, HTTPException
from routers import BASE_PATH, SCIM_Response
from typing import Any
from schema import SCIM_API_MESSAGES, ListResponse, Schemas

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=BASE_PATH+"/Schemas",
    tags=["SCIM Schemas"],
)


@router.get("", response_class=SCIM_Response)
async def get_schemas() -> ListResponse:
    """ Return Schemas """

    resources = []

    for schema in Schemas.keys():
        resources.append(
            Schemas[schema].model_json_schema(by_alias=True)
        )

    return ListResponse(
        Resources=resources,
        itemsPerPage=len(resources),
        schemas=[
            SCIM_API_MESSAGES+":ListResponse"
        ],
        startIndex=1,
        totalResults=len(resources)
    )


@router.get("/{id}", response_class=SCIM_Response)
async def get_schema(id: str) -> Any:
    """ Return Schemas """

    resource = Schemas.get(id)
    logger.debug(resource)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Schema {id} not found")

    return resource.model_json_schema(by_alias=True)
