from schema import ListResponse, User
from typing import Any

from fastapi import APIRouter, Body, status, HTTPException
from data.users import \
    get_user_resources, \
    get_user_resource, \
    put_user_resource, \
    del_user_resource

router = APIRouter(
    prefix="/Users",
    tags=["SCIM Users"],
)


@router.get("")
async def get_all_users(startIndex=1, count=100, filter=None) -> ListResponse:
    """ Read all Users """

    startIndex = max(1, startIndex)
    count = max(0, count)

    totalResults = (get_user_resources(filter) or [])
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
async def create_user(
    user: User = Body(
        example={
            "externalId": "string",
            "active": True,
            "name": {
                "familyName": "string",
                "givenName": "string"
            },
            "displayName": "string",
            "emails": [
                {
                    "primary": True,
                    "value": "string"
                }
            ],
            "userName": "string",
            "urn:mace:surf.nl:sram:scim:extension:User": {},
            "x509Certificates": [
                {
                    "value": "string"
                }
            ],
            "schemas": [
                "string"
            ]
        },
    ),
) -> Any:
    """ Create a User """

    resource = put_user_resource(None, user)
    return resource.dict(exclude_none=True)


@router.get("/{id}")
async def get_user(id: str) -> Any:
    """ Read a User """
    resource = get_user_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"User {id} not found")

    return resource.dict(exclude_none=True)


@router.put("/{id}")
async def update_user(id: str, user: User):
    """ Update a User """
    resource = put_user_resource(id, user)
    if not resource:
        raise HTTPException(status_code=404, detail=f"User {id} not found")
    return resource.dict(exclude_none=True)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(id: str):
    """ Delete a User """
    resource = get_user_resource(id)
    if resource:
        del_user_resource(id)
