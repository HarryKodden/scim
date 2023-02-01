# data/users.py

import os

from typing import Any
from datetime import datetime
from schema import UserResource, User, Meta
from filter import Filter

from data import generate_uuid, PATH_USERS, read, write


def del_user_resource(id: str) -> None:
    os.unlink(f"{PATH_USERS}/{id}")


def get_user_resource(id: str) -> UserResource:
    data = read(f"{PATH_USERS}/{id}")
    if not data:
        return None

    return UserResource(**data)


def get_user_resources(filter: Filter) -> [Any]:
    result: Any = []

    for id in os.listdir(PATH_USERS):
        resource = get_user_resource(id)
        if filter.match(resource):
            result.append(resource.dict(by_alias=True, exclude_none=True))

    return result


def lookup_user(userName: str) -> UserResource:
    for user in get_user_resources():
        if user.userName == userName:
            return user

    return None


def put_user_resource(id: str, user: User) -> UserResource:
    if id:
        resource = get_user_resource(id)
        if not resource:
            return None
    else:
        id = generate_uuid()

        resource = UserResource(
            id=id,
            userName=user.userName,
            active=user.active,
            meta=Meta(
                resourceType='User',
                location=f"/Users/{id}"
            )
        )

    resource.active = user.active
    resource.userName = user.userName
    resource.displayName = user.displayName
    resource.externalId = user.externalId
    resource.emails = user.emails
    resource.sram_user_extension = user.sram_user_extension
    resource.x509Certificates = user.x509Certificates
    resource.meta.lastModified = datetime.now()
    resource.schemas = [
        "urn:ietf:params:scim:schemas:core:2.0:user"
    ]

    write(
        f"{PATH_USERS}/{id}",
        resource.json()
    )

    return resource
