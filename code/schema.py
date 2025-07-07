# schema.py

import os
import json

from pathlib import Path
from datetime import datetime
from typing import Union, List, Optional, Dict, Literal, Any
from pydantic import BaseModel, Field, create_model

import logging
logging.basicConfig(level="DEBUG")
logger = logging.getLogger(__name__)

# SCIM 2.0 Core Schema URIs
CORE_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0"
CORE_SCHEMA_USER = CORE_SCHEMA+":User"
CORE_SCHEMA_GROUP = CORE_SCHEMA+":Group"

# SCIM 2.0 API URIs
SCIM_API_MESSAGES = "urn:ietf:params:scim:api:messages:2.0"

# SCIM 2.0 Patch Operation URIs
SCIM_PATCH_OP = SCIM_API_MESSAGES + ":PatchOp"

# SCIM 2.0 Content Types
SCIM_CONTENT_TYPE = 'application/scim+json'

SCHEMA_DIR = os.environ.get(
    'SCHEMA_PATH',
    str(Path(__file__).parent.parent / "schemas")
)

resourceTypes = []

Schemas = {
    "User": {},
    "Group": {},
}

global User, UserResource, Group, GroupResource


class HealthCheck(BaseModel):
    status: str = "OK"


class Operation(BaseModel):
    op: Literal[
        "add", "Add", "ADD",
        "remove", "Remove", "REMOVE",
        "replace", "Replace", "REPLACE",
    ]
    path: str
    value: Optional[Any] = None


class Patch(BaseModel):
    schemas: List[str]
    Operations: List[Operation]


class Meta(BaseModel):
    location: str
    resourceType: str
    lastModified: Optional[datetime] = None
    created: Optional[datetime] = None
    version: Optional[str] = None
    etag: Optional[str] = None


class SchemaExtension(BaseModel):
    required: bool = False
    schema_name: str = Field(alias="schema")


class Resource(BaseModel):
    id: str
    meta: Meta
    schemas: Optional[List[str]] = None


class ResourceType(Resource):
    name: str
    description: str
    endpoint: str
    schema_name: str = Field(alias="schema")
    schemaExtensions: Optional[List[Union[SchemaExtension, None]]] = None
    schemas: List[str] = [
        CORE_SCHEMA+":ResourceType"
    ]


class ListResponse(BaseModel):
    totalResults: int
    itemsPerPage: int
    schemas: List[str]
    Resources: List[Any] = Field(alias="Resources")


def register_model(name, attributes, fields={}, __base__=(BaseModel)) -> Any:
    for attr in attributes:
        attr_name = attr.get('name')
        attr_type = attr.get('type', 'string')
        attr_required = attr.get('required', False)
        attr_multi_valued = attr.get('multiValued', False)
        attr_alias = attr.get('alias')

        # Map JSON schema types to Python types
        type_mapping = {
            'string': str,
            'integer': int,
            'boolean': bool,
            'decimal': float,
            'datetime': datetime,
            'reference': str,
            'complex': dict
        }

        python_type = type_mapping.get(attr_type, Any)

        # Handle complex types
        if attr_type == 'complex':
            python_type = register_model(
                f"{name}_{attr_name}",
                attr.get('subAttributes', [])
            )

        # Handle multi-valued attributes
        if attr_multi_valued:
            if python_type is dict:
                python_type = List[Dict[str, Any]]
            else:
                python_type = List[python_type]

        # Handle fields
        # - optional: Y/N
        # - alias: Y/N
        if not attr_required and attr_alias:
            fields[attr_name] = (
                Optional[python_type],
                Field(default=None, alias=attr_alias)
            )
        elif not attr_required:
            fields[attr_name] = (Optional[python_type], None)
        elif attr_alias:
            fields[attr_name] = (python_type, Field(alias=attr_alias))
        else:
            fields[attr_name] = (python_type, None)

    # Create dynamic Pydantic model
    logger.debug(f"Create Model: {name} with fields: {fields}")

    return create_model(
        name,
        __base__=__base__,
        **fields,
    )
    fields = {}


def register_resource_type(resource_name, schema_uri, attributes):
    """
    Register a resource type with its schema
    and create associated models.
    """

    logger.debug(f"Registering resource type: {resource_name}")
    # Prepare optional fields for all defined extension models
    fields = {}
    for id, model in Schemas[resource_name].items():
        fields[model.__name__] = (
            Optional[model], Field(alias=id, default=None)
        )

    model = register_model(
        resource_name,
        attributes,
        fields=fields
    )

    # Create the resource model by extending base model with Resource
    resource_model = create_model(
        f"{resource_name}Resource",
        __base__=(model, Resource),
    )

    # Store in Schemas dictionary
    Schemas[resource_name][schema_uri] = resource_model

    # Add to ResourceType collection
    resourceTypes.append(
        ResourceType(
            id=resource_name,
            name=resource_name,
            description=f"Resource type for the {resource_name} schema",
            endpoint=f"/{resource_name}s",  # Pluralize endpoint
            meta=Meta(
                location=f"/ResourceTypes/{resource_name}",
                resourceType="ResourceType"
            ),
            schemaExtensions=[],
            schema=schema_uri
        )
    )

    # Return the created models to assign to global variables
    return model, resource_model


for resource in ['User', 'Group']:
    # First create the extension models...
    extensions = os.path.join(SCHEMA_DIR, f"extensions/{resource}")

    if os.path.exists(extensions):
        for filename in os.listdir(extensions):
            logger.debug(f"Loading extension schema from: {filename}...")

            if filename.endswith('.json'):
                filepath = os.path.join(extensions, filename)
                try:
                    with open(filepath, 'r') as f:
                        schema_data = json.load(f)

                    # Extract schema information
                    name = Path(filename).stem
                    id = schema_data.get('id', name)
                    attributes = schema_data.get('attributes', [])

                    Schemas[resource][id] = register_model(
                        f"{resource}_{name}", attributes
                    )

                except Exception as e:
                    logger.error(
                        f"Error loading schema from {filepath}: {str(e)}"
                    )

    # Now load core schema for this resource...
    try:
        core_schema_path = os.path.join(
            SCHEMA_DIR, f"core/{resource}.json"
        )
        logger.debug(f"Loading core schema from: {core_schema_path}")

        with open(core_schema_path, 'r') as f:
            schema_data = json.load(f)

        attributes = schema_data.get('attributes', [])

        if resource == 'User':
            User, UserResource = register_resource_type(
                'User', CORE_SCHEMA_USER, attributes
            )
        elif resource == 'Group':
            Group, GroupResource = register_resource_type(
                'Group', CORE_SCHEMA_GROUP, attributes
            )
        else:
            raise ValueError(f"Unknown resource type: {resource}")

    except Exception as e:
        print(f"Error loading core schema {resource}: {str(e)}")

for s in Schemas:
    logger.debug(f"Schema: {s} -> {Schemas[s]}")

for r in resourceTypes:
    logger.debug(f"Resource: {r.id} -> {r}")
