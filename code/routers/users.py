# routers/users.py

from fastapi import APIRouter, Body, status, HTTPException, Query

from schema import ListResponse, User
from typing import Any
from routers import BASE_PATH, get_all_resources

from data.users import \
    get_user_resource, \
    put_user_resource, \
    del_user_resource

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=BASE_PATH+"/Users",
    tags=["SCIM Users"],
)


@router.get("")
async def get_all_users(
    startindex: int = Query(default=1, alias='startIndex'),
    count: int = Query(default=100, alias='count'),
    query: str = Query(default='', alias='filter')
) -> ListResponse:
    """ Read all Groups """
    return get_all_resources('User', startindex, count, query)


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
            "urn:mace:surf.nl:sram:scim:extension:User": {
                "eduPersonScopedAffiliation": "string",
                "eduPersonUniqueId": "string",
                "voPersonExternalAffiliation": "string",
                "voPersonExternalId": "string"
            },
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

    try:
        resource = put_user_resource(None, user)
        return resource.dict(by_alias=True, exclude_none=True)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error: {str(e)}")


@router.get("/{id}")
async def get_user(id: str) -> Any:
    """ Read a User """
    resource = get_user_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"User {id} not found")

    return resource.dict(by_alias=True, exclude_none=True)


@router.put("/{id}")
async def update_user(id: str, user: User):
    """ Update a User """

    try:
        resource = put_user_resource(id, user)
        if not resource:
            raise Exception(f"User {id} not found")

        return resource.dict(exclude_none=True)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error: {str(e)}")


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(id: str):
    """ Delete a User """
    resource = get_user_resource(id)
    if resource:
        del_user_resource(id)
