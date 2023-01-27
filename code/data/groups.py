import os

from datetime import datetime
from schema import GroupResource, Group
from data import generate_uuid, PATH_GROUPS, logger, read, write


def del_group_resource(id: str) -> None:
    os.unlink(f"{PATH_GROUPS}/{id}")


def get_group_resource(id: str) -> GroupResource:
    data = read(f"{PATH_GROUPS}/{id}")
    if not data:
      return None

    return GroupResource(**data)


def get_group_resources() -> [ GroupResource ]:
  result: GroupResource = []

  for id in os.listdir(PATH_GROUPS):
    result.append(get_group_resource(id))

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
          resourceType = 'Group',
          location = f"/Groups/{id}"
        )
      )

    if group.displayName:
      resource.displayName = group.displayName

    if group.externalId:
      resource.externalId = group.externalId

    if group.members:
      resource.members = group.members

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