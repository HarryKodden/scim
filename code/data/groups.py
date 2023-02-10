# data/groups.py

from typing import Any
from datetime import datetime
from schema import GroupResource, Group, Meta
from filter import Filter

from data import generate_uuid, iterate, read, write, delete
from data.users import get_user_resource


def del_group_resource(id: str) -> None:
    delete("Groups", id)


def get_group_resource(id: str) -> GroupResource:
    data = read("Groups", id)
    if not data:
        return None

    return GroupResource(**data)


def get_group_resources(filter: Filter) -> [Any]:
    result: Any = []

    for id in iterate("Groups"):
        resource = get_group_resource(id)
        if filter.match(resource):
            result.append(resource.dict(by_alias=True, exclude_none=True))

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
            displayName=group.displayName,
            meta=Meta(
                resourceType='Group',
                location=f"/Groups/{id}"
            )
        )

    resource.displayName = group.displayName
    resource.externalId = group.externalId
    resource.members = group.members
    for member in resource.members or []:
        user = get_user_resource(member.value)
        if not user:
            raise Exception(f"Member: {member.value} not existing")

        member.displayName = user.displayName

    resource.sram_group_extension = group.sram_group_extension
    resource.meta.lastModified = datetime.now()
    resource.schemas = [
        "urn:ietf:params:scim:schemas:core:2.0:Group"
    ]

    write("Groups", id, resource.json())

    return resource
