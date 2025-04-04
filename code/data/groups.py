# data/groups.py

import os
import json

from typing import Any
from datetime import datetime
from schema import CORE_SCHEMA_GROUP, Schemas, GroupResource, Group, Meta
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
                json.loads(
                    resource.model_dump_json(by_alias=True, exclude_none=True)
                )
            )

    return result


def put_group_resource(id: str, group: Group) -> GroupResource:
    for member in group.members or []:
        user = get_user_resource(member.value)
        if not user:
            raise Exception(f"Member: '{member.value}' not existing")

        member.display = user.displayName
        member.ref = f"/Users/{user.id}"

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

    resource.schemas = [
        CORE_SCHEMA_GROUP
    ]

    # Generic field copying from group to resource
    for field in vars(group):
        if (hasattr(resource, field)):

            for id in Schemas['Group']:
                if id not in resource.schemas and field.startswith(id):
                    resource.schemas.append(id)

            setattr(resource, field, getattr(group, field))

    # Scan top level fields to see if they belong to extension schemas
    # and add them to the schemas list
    for field in resource.model_dump(by_alias=True, exclude_none=True):
        if field in Schemas['Group'] and field not in resource.schemas:
            resource.schemas.append(field)

    resource.meta.lastModified = datetime.now()

    mapping = json.loads(os.environ.get('GROUP_MAPPING', "{}"))
    for k, v in mapping.items():
        logger.debug(f"[MAPPING] {k} := {v}")

        value = resource
        for f in v.split('.'):
            value = getattr(value, f)

        logger.debug(f"[MAPPING VALUE] {value}")

        setattr(resource, k, value)

    id = resource.id

    Groups[id] = resource.model_dump_json(by_alias=True, exclude_none=True)

    return get_group_resource(id)


def remove_member(group: GroupResource, id) -> bool:
    for i in range(len(group.members or [])):
        if group.members[i].value == id:
            group.members = group.members[:i] + group.members[i+1:]
            Groups[group.id] = group.model_dump_json(
                by_alias=True, exclude_none=True
            )
            return True
    return False
