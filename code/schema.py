# schema.py

from datetime import datetime

from typing import Union, List, Optional, Dict, Literal, Any

from pydantic import BaseModel, Field

CORE_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0"
CORE_SCHEMA_USER = CORE_SCHEMA+":User"
CORE_SCHEMA_GROUP = CORE_SCHEMA+":Group"

SRAM_SCHEMA = "urn:mace:surf.nl:sram:scim:extension"
SRAM_SCHEMA_USER = SRAM_SCHEMA+":User"
SRAM_SCHEMA_GROUP = SRAM_SCHEMA+":Group"

SCIM_API_MESSAGES = "urn:ietf:params:scim:api:messages:2.0"

SCIM_CONTENT_TYPE = 'application/scim+json'


class HealthCheck(BaseModel):
    status: str = "OK"


class Operation(BaseModel):
    op: Literal["add", "remove", "replace"]
    path: str
    value: Optional[Any] = None


class Patch(BaseModel):
    schemas: List[str]
    operations: List[Operation]


class Name(BaseModel):
    familyName: str
    givenName: str


class Email(BaseModel):
    primary: bool
    value: str


class Member(BaseModel):
    ref: Optional[str] = Field(alias="$ref", default=None)
    display: Optional[str] = None
    value: str


class Link(BaseModel):
    name: str
    value: str


class Certificate(BaseModel):
    value: str


class Meta(BaseModel):
    created: datetime = Field(default_factory=datetime.now)
    lastModified: datetime = Field(default_factory=datetime.now)
    location: Optional[str] = None
    resourceType: str


class ListResponse(BaseModel):
    Resources: Optional[List[Dict]] = None
    itemsPerPage: int
    schemas: List[str]
    startIndex: int
    totalResults: int


class SRAM_User_Extension(BaseModel):
    eduPersonScopedAffiliation: Optional[str] = None
    eduPersonUniqueId: Optional[str] = None
    voPersonExternalAffiliation: Optional[str] = None
    voPersonExternalId: Optional[str] = None
    sramInactiveDays: Optional[int] = None

#   class Config:
#       title = "SRAM User Extension"


class SRAM_Group_Extension(BaseModel):
    description: Optional[str] = None
    labels: Optional[List[str]] = None
    urn: Optional[str] = None
    links: Optional[List[Union[Link, None]]] = None

#   class Config:
#       title = "SRAM Group Extension"


class User(BaseModel):
    userName: str
    active: bool = True
    externalId: Optional[str] = None
    name: Optional[Name] = None
    displayName: Optional[str] = None
    emails: Optional[List[Union[Email, None]]] = None
    sram_user_extension: Optional[SRAM_User_Extension] = \
        Field(alias=SRAM_SCHEMA_USER, default=None)
    x509Certificates: Optional[List[Union[Certificate, None]]] = None
    schemas: Optional[List[Union[str, None]]] = None


class UserResource(User):
    id: str
    meta: Meta

#   class Config:
#       title = "User"


class Group(BaseModel):
    displayName: str
    externalId: Optional[str] = None
    members: Optional[List[Union[Member, None]]] = []
    sram_group_extension: Optional[SRAM_Group_Extension] = \
        Field(alias=SRAM_SCHEMA_GROUP, default=None)
    schemas: List[Union[str, None]] = None


class GroupResource(Group):
    id: str
    meta: Meta

#   class Config:
#       title = "Group"


class SchemaExtension(BaseModel):
    required: bool = False
    schema_name: str = Field(alias="schema")


class ResourceType(BaseModel):
    id: str
    name: str
    description: str
    endpoint: str
    meta: Meta
    schema_name: str = Field(alias="schema")
    schemaExtensions: Optional[List[Union[SchemaExtension, None]]] = None
    schemas: List[Union[str, None]] = [
        CORE_SCHEMA+":ResourceType"
    ]


Schemas = {
    CORE_SCHEMA_USER: UserResource,
    CORE_SCHEMA_GROUP: GroupResource,
    SRAM_SCHEMA_USER: SRAM_User_Extension,
    SRAM_SCHEMA_GROUP: SRAM_Group_Extension,
}

resourceTypes = [
    ResourceType(
        name="User",
        id="User",
        description="Defined resource types for the User schema",
        endpoint="/Users",
        meta=Meta(
            location="/ResourceTypes/User",
            resourceType="ResourceType"
        ),
        schemaExtensions=[
            SchemaExtension(
                schema=SRAM_SCHEMA_USER
            )
        ],
        schema=CORE_SCHEMA_USER,
    ),
    ResourceType(
        name="Group",
        id="Group",
        description="Defined resource types for the Group schema",
        endpoint="/Groups",
        meta=Meta(
            location="/ResourceTypes/Group",
            resourceType="ResourceType"
        ),
        schemaExtensions=[
            SchemaExtension(
                schema=SRAM_SCHEMA_GROUP
            )
        ],
        schema=CORE_SCHEMA_GROUP,
    ),
]
