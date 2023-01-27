from datetime import datetime
from typing import ClassVar, Union, List, Optional, Dict
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class Name(BaseModel):
    familyName: str
    givenName: str


class Email(BaseModel):
    primary: bool
    value: str


class Member(BaseModel):
    ref: ClassVar[str] = Field(alias="$ref")
    displayName: str
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
    voPersonExternalAffiliation: List[str] = []
    voPersonExternalId: str = None


class SRAM_Group_Extension(BaseModel):
    description: str = None
    labels: Optional[List[str]]
    urn: str = None


class User(BaseModel):
    externalId: str = None
    active: bool = None
    name: Name = None
    displayName: str = None
    emails: List[Union[Email, None]] = None
    userName: str = None
    sram_user_extension: Optional[SRAM_User_Extension] = Field(alias="urn:mace:surf.nl:sram:scim:extension:User", default={})
    x509Certificates: List[Union[Certificate, None]] = None
    schemas: List[Union[str, None]] = None


class UserResource(BaseModel):
    id: str = None
    externalId: str = None
    active: bool = True
    name: Name = None
    displayName: str = None
    emails: List[Union[Email, None]] = None
    userName: str = None
    sram_user_extension: Optional[SRAM_User_Extension] = Field(alias="urn:mace:surf.nl:sram:scim:extension:User", default={})
    x509Certificates: List[Union[Certificate, None]] = None
    schemas: List[Union[str, None]] = None
    meta: Meta = None
    hashed_password: str = None


class Group(BaseModel):
    externalId: str = None
    displayName: str = None
    members: List[Union[Member, None]] = None
    schemas: List[Union[str, None]] = None
    sram_group_extension: Optional[SRAM_Group_Extension] = Field(alias="urn:mace:surf.nl:sram:scim:extension:Group", default={})
    meta: Meta = None


class GroupResource(BaseModel):
    id: str = None
    externalId: str = None
    displayName: str = None
    members: List[Union[Member, None]] = None
    schemas: List[Union[str, None]] = None
    sram_group_extension: Optional[SRAM_Group_Extension] = Field(alias="urn:mace:surf.nl:sram:scim:extension:Group", default={})
    meta: Meta = None