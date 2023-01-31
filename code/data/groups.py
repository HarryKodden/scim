# data/groups.py

import os

from typing import Any
from datetime import datetime
from schema import GroupResource, Group, Meta
from filter import Filter

from data import generate_uuid, PATH_GROUPS, read, write
from data.users import get_user_resource


def del_group_resource(id: str) -> None:
    os.unlink(f"{PATH_GROUPS}/{id}")


def get_group_resource(id: str) -> GroupResource:
    data = read(f"{PATH_GROUPS}/{id}")
    if not data:
        return None

    return GroupResource(**data)


def get_group_resources(filter: Filter) -> [Any]:
    result: Any = []

    for id in os.listdir(PATH_GROUPS):
        resource = get_group_resource(id)
        if filter.match(resource):
            result.append(resource.dict(exclude_none=True))

    return result


def put_group_resource(id: str, group: Group) -> GroupResource:
    if id:
        resource = get_group_resource(id)
        if not resource:
            return None
    else:
        id = generate_uuid()

        resource = GroupResource(
            id=id,
            meta=Meta(
                resourceType='Group',
                location=f"/Groups/{id}"
            )
        )

    if group.displayName:
        resource.displayName = group.displayName

    if group.externalId:
        resource.externalId = group.externalId

    if group.members:
        resource.members = group.members

    for member in resource.members:
        user = get_user_resource(member.value)
        if not user:
            raise Exception(f"Member: {member.value} not existing")

        member.displayName = user.displayName

    if group.sram_group_extension:
        resource.sram_group_extension = group.sram_group_extension

    resource.meta.lastModified = datetime.now()

    resource.schemas = [
        "urn:ietf:params:scim:schemas:core:2.0:Group"
    ]

    write(
        f"{PATH_GROUPS}/{id}",
        resource.json()
    )

    return resource
