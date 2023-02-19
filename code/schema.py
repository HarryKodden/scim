# schema.py

from datetime import datetime
from typing import ClassVar, Union, List, Optional, Dict
from pydantic import BaseModel, Field

CORE_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0"
CORE_SCHEMA_USER = CORE_SCHEMA+":User"
CORE_SCHEMA_GROUP = CORE_SCHEMA+":Group"

SRAM_SCHEMA = "urn:mace:surf.nl:sram:scim:extension"
SRAM_SCHEMA_USER = SRAM_SCHEMA+":User"
SRAM_SCHEMA_GROUP = SRAM_SCHEMA+":Group"

SCIM_API_MESSAGES = "urn:ietf:params:scim:api:messages:2.0"


class Name(BaseModel):
    familyName: str
    givenName: str


class Email(BaseModel):
    primary: bool
    value: str


class Member(BaseModel):
    ref: ClassVar[str] = Field(alias="$ref")
    displayName: str = None
    value: str


class Certificate(BaseModel):
    value: str


class Meta(BaseModel):
    created: datetime = Field(default_factory=datetime.utcnow)
    lastModified: datetime = Field(default_factory=datetime.utcnow)
    location: str
    resourceType: str


class ListResponse(BaseModel):
    Resources: List[Dict] = None
    itemsPerPage: int
    schemas: List[str]
    startIndex: int
    totalResults: int


class SRAM_User_Extension(BaseModel):
    eduPersonScopedAffiliation: str = None
    eduPersonUniqueId: str = None
    voPersonExternalAffiliation: str = None
    voPersonExternalId: str = None

    class Config:
        title = "SRAM User Extension"


class SRAM_Group_Extension(BaseModel):
    description: str = None
    labels: Optional[List[str]]
    urn: str = None

    class Config:
        title = "SRAM Group Extension"


class User(BaseModel):
    userName: str
    active: bool = True
    externalId: str = None
    name: Name = None
    displayName: str = None
    emails: List[Union[Email, None]] = None
    sram_user_extension: Optional[SRAM_User_Extension] = \
        Field(alias=SRAM_SCHEMA_USER, default=None)
    x509Certificates: List[Union[Certificate, None]] = None
    schemas: List[Union[str, None]] = None


class UserResource(User):
    id: str
    meta: Meta

    class Config:
        title = "User"


class Group(BaseModel):
    displayName: str
    externalId: str = None
    members: List[Union[Member, None]] = None
    sram_group_extension: Optional[SRAM_Group_Extension] = \
        Field(alias=SRAM_SCHEMA_GROUP, default=None)
    schemas: List[Union[str, None]] = None


class GroupResource(Group):
    id: str
    meta: Meta

    class Config:
        title = "Group"


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
    schemaExtensions: List[Union[SchemaExtension, None]] = None
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
