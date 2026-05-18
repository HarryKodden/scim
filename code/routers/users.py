# routers/users.py

import json

from fastapi import APIRouter, Depends, Body, status, HTTPException, Query, Request, Response
from pydantic_core import from_json, ValidationError

import traceback

from schema import ListResponse, User, Patch, GroupResource, \
    SCIM_PATCH_OP
from typing import Any
from auth import api_key_auth

from routers import BASE_PATH, PAGE_SIZE, \
    get_all_resources, resource_exists, patch_resource, \
    SCIM_Route, SCIM_Response

from events.feed_events import emit_feed_remove
from events.feed_registry import resolve_feed_for_group
from events.publisher import emit_group_event, emit_user_event, emit_user_lifecycle_event
from versioning import check_if_match, detect_active_change, dump_resource

# Needed to update groups when User resource is deleted
# which is a member of a group
from data.groups import get_group_resources, remove_member
from filter import Filter

from data.users import \
    get_user_resource, \
    put_user_resource, \
    del_user_resource

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    route_class=SCIM_Route,
    prefix=BASE_PATH+"/Users",
    tags=["SCIM Users"],
    dependencies=[Depends(api_key_auth)]
)


@router.get("", response_class=SCIM_Response)
async def get_all_users(
    startindex: int = Query(default=1, alias='startIndex'),
    count: int = Query(default=PAGE_SIZE, alias='count'),
    query: str = Query(default='', alias='filter')
) -> ListResponse:
    """ Read all Groups """
    return get_all_resources('User', startindex, count, query)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_class=SCIM_Response
)
async def create_user(
    response: Response,
    user: User = Body(
        examples={
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

    if resource_exists(
        "User",
        f"userName eq \"{user.userName}\""
    ):
        raise HTTPException(
            status_code=409,
            detail="userName already exists"
        )

    if user.externalId:
        if resource_exists(
            "User",
            f"externalId eq \"{user.externalId}\""
        ):
            raise HTTPException(
                status_code=409,
                detail="User already exists with same externalId"
            )

    try:
        resource = put_user_resource(None, user)

        emit_user_event("create", resource, base_path=BASE_PATH)

        return dump_resource(resource, response)
    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail="Invalid User resource"
        )
    except Exception as e:
        logger.error(f"[CREATE_USER] {str(e)}, {traceback.format_exc()}")
        raise HTTPException(
            status_code=404,
            detail=f"Error: {str(e)}"
        )


@router.get("/{id}", response_class=SCIM_Response)
async def get_user(id: str, response: Response) -> Any:
    """ Read a User """
    resource = get_user_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"User {id} not found")

    return dump_resource(resource, response)


@router.put("/{id}", response_class=SCIM_Response)
async def update_user(id: str, user: User, request: Request, response: Response):
    """ Update a User Resource """

    existing = get_user_resource(id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"User {id} not found")
    check_if_match(request, existing.meta.version)

    if resource_exists(
        "User",
        f"userName eq \"{user.userName}\" and id ne \"{id}\""
    ):
        raise HTTPException(
            status_code=409,
            detail="userName already exists"
        )

    if user.externalId:
        if resource_exists(
                "User",
                f"externalId eq \"{user.externalId}\" and id ne \"{id}\""
        ):
            raise HTTPException(
                status_code=409,
                detail="User already exists with same externalId"
            )

    try:
        resource = put_user_resource(id, user)
        if not resource:
            raise Exception(f"User {id} not found")

        emit_user_event("put", resource, base_path=BASE_PATH)
        lifecycle = detect_active_change(existing, resource)
        if lifecycle:
            emit_user_lifecycle_event(lifecycle, resource, base_path=BASE_PATH)

        return dump_resource(resource, response)

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error: {str(e)}")


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(id: str):
    """ Delete a User Resource """
    resource = get_user_resource(id)
    if resource:
        groups = get_group_resources(Filter(f"members[value eq \"{id}\"]"))
        for g in groups:
            logger.debug(f"[GROUP]: {g}")

            group = GroupResource.model_validate(
                from_json(
                    json.dumps(g)
                )
            )
            if remove_member(group, id):
                emit_group_event("patch", group, base_path=BASE_PATH)
                emit_feed_remove(
                    resource,
                    "User",
                    resolve_feed_for_group(group.id),
                    base_path=BASE_PATH,
                )

        emit_user_event("delete", resource, base_path=BASE_PATH)
        del_user_resource(id)


@router.patch("/{id}", response_class=SCIM_Response)
async def patch_user(id: str, patch: Patch, request: Request, response: Response):
    """ Patch a User Resource """
    try:
        user = get_user_resource(id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {id} not found")
        check_if_match(request, user.meta.version)

        if SCIM_PATCH_OP not in patch.schemas:
            raise HTTPException(
                status_code=400,
                detail=f"Missing schema {SCIM_PATCH_OP}"
            )

        before = get_user_resource(id)
        resource = patch_resource(
            user.model_dump(by_alias=True, exclude_none=True),
            patch.Operations
        )

        user = put_user_resource(id, User(**resource))

        emit_user_event(
            "patch",
            user,
            patch_operations=patch.Operations,
            base_path=BASE_PATH,
        )
        lifecycle = detect_active_change(before, user)
        if lifecycle:
            emit_user_lifecycle_event(lifecycle, user, base_path=BASE_PATH)

        return dump_resource(user, response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
