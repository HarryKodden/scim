# routers/groups.py

from task_runner import (
    CHANGE_TYPE_CREATE, CHANGE_TYPE_UPDATE, CHANGE_TYPE_DELETE,
    RESOURCE_TYPE_GROUP, call_change_webhook_task
)
from fastapi import APIRouter, Depends, Body, status, HTTPException, Query

from schema import ListResponse, Group, Patch
from typing import Any
from auth import api_key_auth

from routers import BASE_PATH, PAGE_SIZE, \
    get_all_resources, resource_exists, patch_resource, \
    SCIM_Route, SCIM_Response

from data.groups import \
    get_group_resource, \
    put_group_resource, \
    del_group_resource

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    route_class=SCIM_Route,
    prefix=BASE_PATH+"/Groups",
    tags=["SCIM Groups"],
    dependencies=[Depends(api_key_auth)]
)


@router.get("", response_class=SCIM_Response)
async def get_all_groups(
    startindex: int = Query(default=1, alias='startIndex'),
    count: int = Query(default=PAGE_SIZE, alias='count'),
    query: str = Query(default='', alias='filter')
) -> ListResponse:
    """ Read all Groups """
    return get_all_resources('Group', startindex, count, query)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_class=SCIM_Response
)
async def create_group(
    group: Group = Body(
        examples={
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

    if group.externalId:
        if resource_exists(
            "Group",
            f"externalId eq \"{group.externalId}\""
        ):
            raise HTTPException(
                status_code=409,
                detail="Group already exists with same externalId"
            )

    try:
        resource = put_group_resource(None, group)
        response = resource.model_dump(by_alias=True, exclude_none=True)
        call_change_webhook_task(
            response, CHANGE_TYPE_CREATE, RESOURCE_TYPE_GROUP
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error: {str(e)}")


@router.get("/{id}", response_class=SCIM_Response)
async def get_group(id: str) -> Any:
    """ Read a Group """
    resource = get_group_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Group {id} not found")

    return resource.model_dump(by_alias=True, exclude_none=True)


@router.put("/{id}", response_class=SCIM_Response)
async def update_group(id: str, group: Group):
    """ Update a Group Resource"""

    if group.externalId:
        if resource_exists(
            "Group",
            f"externalId eq \"{group.externalId}\" and id ne \"{id}\""
        ):
            raise HTTPException(
                status_code=409,
                detail="Group already exists with same externalId"
            )

    try:
        resource = put_group_resource(id, group)
        if not resource:
            raise Exception(f"Group {id} not found")
        response = resource.model_dump(by_alias=True, exclude_none=True)
        call_change_webhook_task(
            response, CHANGE_TYPE_UPDATE, RESOURCE_TYPE_GROUP
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error: {str(e)}")


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(id: str):
    """ Delete a Group Resource"""
    resource = get_group_resource(id)
    if resource:
        del_group_resource(id)
        response = resource.model_dump(by_alias=True, exclude_none=True)
        call_change_webhook_task(
            response, CHANGE_TYPE_DELETE, RESOURCE_TYPE_GROUP
        )


@router.patch("/{id}", response_class=SCIM_Response)
async def patch_group(id: str, patch: Patch):
    """ Patch a Group Resource """
    try:
        group = get_group_resource(id)
        if not group:
            raise Exception(f"Group {id} not found")

        resource = patch_resource(
            group.model_dump(by_alias=True, exclude_none=True),
            patch.operations
        )

        group = put_group_resource(id, Group(**resource))
        return group.model_dump(by_alias=True, exclude_none=True)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error: {str(e)}")
