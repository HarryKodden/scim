# schema.py

from datetime import datetime
from typing import ClassVar, Union, List, Optional, Dict
from pydantic import BaseModel, Field

CORE_SCHEMA_USER = "urn:ietf:params:scim:schemas:core:2.0:User"
CORE_SCHEMA_GROUP = "urn:ietf:params:scim:schemas:core:2.0:Group"
SRAM_SCHEMA_USER = "urn:mace:surf.nl:sram:scim:extension:User"
SRAM_SCHEMA_GROUP = "urn:mace:surf.nl:sram:scim:extension:Group"


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
    id: str = None
    meta: Meta = None

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
    id: str = None
    meta: Meta = None

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
        "urn:ietf:params:scim:schemas:core:2.0:ResourceType"
    ]
