# data/users.py

import os
import json

from typing import Any
from datetime import datetime
from schema import CORE_SCHEMA_USER, SRAM_SCHEMA_USER, UserResource, User, Meta
from filter import Filter

from data import Users

import logging
logger = logging.getLogger(__name__)


def del_user_resource(id: str) -> None:
    del Users[id]


def get_user_resource(id: str) -> UserResource:
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
                resource.model_dump(by_alias=True, exclude_none=True)
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

    resource.active = user.active
    resource.name = user.name
    resource.userName = user.userName
    resource.displayName = user.displayName
    resource.externalId = user.externalId
    resource.emails = user.emails
    resource.sram_user_extension = user.sram_user_extension
    resource.x509Certificates = user.x509Certificates
    resource.meta.lastModified = datetime.now()
    resource.schemas = [
        CORE_SCHEMA_USER,
        SRAM_SCHEMA_USER
    ]

    mapping = json.loads(os.environ.get('USER_MAPPING', ""))
    for k, v in mapping.items():
        logger.debug(f"[MAPPING] {k} := {v}")

        value = user
        for f in v.split('.'):
            value = getattr(value, f)

        logger.debug(f"[MAPPING VALUE] {value}")

        setattr(resource, k, value)

    Users[id] = resource.model_dump_json(by_alias=True, exclude_none=True)

    return get_user_resource(id)
