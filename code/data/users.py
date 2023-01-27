import os

from datetime import datetime
from schema import UserResource, User, Meta
from data import generate_uuid, PATH_USERS, read, write


def del_user_resource(id: str) -> None:
    os.unlink(f"{PATH_USERS}/{id}")


def get_user_resource(id: str) -> UserResource:
    data = read(f"{PATH_USERS}/{id}")
    if not data:
        return None

    return UserResource(**data)


def get_user_resources() -> [UserResource]:
    result: UserResource = []

    for id in os.listdir(PATH_USERS):
        result.append(get_user_resource(id))

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
            meta=Meta(
                resourceType='User',
                location=f"/Users/{id}"
            )
        )

    resource.active = user.active

    if user.name:
        resource.name = user.name

    if user.displayName:
        resource.displayName = user.displayName

    if user.externalId:
        resource.externalId = user.externalId

    if user.emails:
        resource.emails = user.emails

    if user.userName:
        resource.userName = user.userName

    if user.sram_user_extension:
        resource.sram_user_extension = user.sram_user_extension

    if user.x509Certificates:
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
