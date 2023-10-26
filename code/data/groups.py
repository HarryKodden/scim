# data/groups.py

from typing import Any
from datetime import datetime
from schema import CORE_SCHEMA_GROUP, SRAM_SCHEMA_GROUP, \
    GroupResource, Group, Meta
from filter import Filter
from data import Groups
from data.users import get_user_resource

import logging
logger = logging.getLogger(__name__)


def del_group_resource(id: str) -> None:
    del Groups[id]


def get_group_resource(id: str) -> GroupResource:
    data = Groups[id]
    if not data:
        return None

    return GroupResource(**data)


def get_group_resources(filter: Filter) -> [Any]:
    result: Any = []

    for id in Groups:
        resource = get_group_resource(id)
        if filter.match(resource):
            result.append(
                resource.model_dump(by_alias=True, exclude_none=True)
            )

    return result


def put_group_resource(id: str, group: Group) -> GroupResource:
    for member in group.members or []:
        user = get_user_resource(member.value)
        if not user:
            raise Exception(f"Member: '{member.value}'' not existing")

        member.display = user.displayName

    if id:
        resource = get_group_resource(id)
        if not resource:
            return None
    else:
        id = Groups.id()

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
    resource.sram_group_extension = group.sram_group_extension
    resource.meta.lastModified = datetime.now()
    resource.schemas = [
        CORE_SCHEMA_GROUP,
        SRAM_SCHEMA_GROUP
    ]

    Groups[id] = resource.model_dump_json(by_alias=True, exclude_none=True)

    return get_group_resource(id)
