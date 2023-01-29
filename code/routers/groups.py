from schema import ListResponse, Group
from typing import Any

from data.groups import \
    get_group_resources, \
    get_group_resource, \
    put_group_resource, \
    del_group_resource

from fastapi import APIRouter, Body, status, HTTPException

router = APIRouter(
    prefix="/Groups",
    tags=["SCIM Groups"],
)


@router.get("")
async def get_all_groups(startIndex=1, count=100, filter=None) -> ListResponse:
    """ Read all Groups """

    startIndex = max(1, startIndex)
    count = max(0, count)

    totalResults = (get_group_resources(filter) or [])
    resources = totalResults[startIndex-1:][:count]

    return ListResponse(
        Resources=resources,
        itemsPerPage=len(resources),
        schemas=[
            "urn:ietf:params:scim:api:messages:2.0:ListResponse"
        ],
        startIndex=startIndex,
        totalResults=len(totalResults)
    )


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

    resource = put_group_resource(None, group)
    return resource.dict(exclude_none=True)


@router.get("/{id}")
async def get_group(id: str) -> Any:
    """ Read a Group """
    resource = get_group_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Group {id} not found")

    return resource.dict(exclude_none=True)


@router.put("/{id}")
async def update_group(id: str, group: Group):
    """ Update a Group """
    resource = put_group_resource(id, group)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Group {id} not found")
    return resource.dict(exclude_none=True)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(id: str):
    """ Delete a Group """
    resource = get_group_resource(id)
    if resource:
        del_group_resource(id)
