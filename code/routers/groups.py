# routers/groups.py

from fastapi import APIRouter, Body, status, HTTPException, Query

from schema import ListResponse, Group
from routers import BASE_PATH, get_all_resources
from typing import Any

from data.groups import \
    get_group_resource, \
    put_group_resource, \
    del_group_resource

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=BASE_PATH+"/Groups",
    tags=["SCIM Groups"],
)


@router.get("")
async def get_all_groups(
    startindex: int = Query(default=1, alias='startIndex'),
    count: int = Query(default=100, alias='count'),
    query: str = Query(default='', alias='filter')
) -> ListResponse:
    """ Read all Groups """
    return get_all_resources('Group', startindex, count, query)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_group(
    group: Group = Body(
        example={
            "displayName": "Student",
            "externalId": "273aca56-d86a-4f05-a159-51856b5cb1b3@sram.surf.nl",
            "members": [
                {
                    "displayName": "John Doe",
                    "value": "25854263-01ee-4e45-a4de-e34e04e9830b"
                },
                {
                    "displayName": "Peter Doe",
                    "value": "89a7c3ca-1e8b-48ed-bc17-831611078a52"
                },
            ],
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:Group"
            ],
            "urn:mace:surf.nl:sram:scim:extension:Group": {
                "description": "Student users group",
                "labels": [],
                "urn": "uuc:collab01:students"
            }
        },
    ),
) -> Any:
    """ Create a Group """

    try:
        resource = put_group_resource(None, group)
        return resource.dict(by_alias=True, exclude_none=True)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error: {str(e)}")


@router.get("/{id}")
async def get_group(id: str) -> Any:
    """ Read a Group """
    resource = get_group_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Group {id} not found")

    return resource.dict(by_alias=True, exclude_none=True)


@router.put("/{id}")
async def update_group(id: str, group: Group):
    """ Update a Group """
    try:
        resource = put_group_resource(id, group)
        if not resource:
            raise Exception(f"Group {id} not found")
        return resource.dict(by_alias=True, exclude_none=True)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error: {str(e)}")


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(id: str):
    """ Delete a Group """
    resource = get_group_resource(id)
    if resource:
        del_group_resource(id)
