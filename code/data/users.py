# data/users.py

import os
import json

from typing import Optional, Any
from datetime import datetime
from schema import CORE_SCHEMA_USER, Schemas, UserResource, User, Meta
from filter import Filter
from data import Users

import logging
logger = logging.getLogger(__name__)


def del_user_resource(id: str) -> None:
    del Users[id]


def get_user_resource(id: str) -> Optional[UserResource]:
    data = Users[id]
    if not data:
        return None

    return UserResource(**data)


def get_user_resources(filter: Filter) -> [Any]:
    result: Any = []

    for id in Users:
        resource = get_user_resource(id)
        if filter.match(resource):
            result.append(
                json.loads(
                    resource.model_dump_json(by_alias=True, exclude_none=True)
                )
            )

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
        id = Users.id()

        resource = UserResource(
            id=id,
            userName=user.userName,
            active=user.active,
            meta=Meta(
                resourceType='User',
                location=f"/Users/{id}"
            )
        )

    resource.schemas = [
        CORE_SCHEMA_USER
    ]

    # Generic field copying from user to resource
    for field in vars(user):
        if (hasattr(resource, field)):

            for id in Schemas['User']:
                if id not in resource.schemas and field.startswith(id):
                    resource.schemas.append(id)

            setattr(resource, field, getattr(user, field))

    resource.meta.lastModified = datetime.now()

    mapping = json.loads(os.environ.get('USER_MAPPING', "{}"))
    for k, v in mapping.items():
        logger.debug(f"[MAPPING] {k} := {v}")

        value = resource
        for f in v.split('.'):
            value = getattr(value, f)

        logger.debug(f"[MAPPING VALUE] {value}")

        setattr(resource, k, value)

    id = resource.id

    Users[id] = resource.model_dump_json(by_alias=True, exclude_none=True)

    return get_user_resource(id)
