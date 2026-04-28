# schema.py

import os
import json

from pathlib import Path
from datetime import datetime
from typing import Union, List, Optional, Dict, Literal, Any
from pydantic import BaseModel, Field, create_model

import logging
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
SchemaResources = {}

global User, UserResource, Group, GroupResource


def normalize_scim_type(attr_type: str) -> str:
    """Return canonical SCIM attribute type value."""
    mapping = {
        "string": "string",
        "boolean": "boolean",
        "booelean": "boolean",
        "integer": "integer",
        "decimal": "decimal",
        "datetime": "dateTime",
        "dateTime": "dateTime",
        "reference": "reference",
        "complex": "complex",
        "binary": "binary",
    }
    return mapping.get(attr_type, attr_type)


def normalize_attribute_definition(attribute: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize schema attribute definition to SCIM-compatible values."""
    normalized = dict(attribute)
    normalized_type = normalize_scim_type(str(normalized.get("type", "string")))
    normalized["type"] = normalized_type

    # RFC7643 schema attribute objects must carry descriptive metadata.
    normalized.setdefault("description", str(normalized.get("name", "")))
    normalized.setdefault("multiValued", False)
    normalized.setdefault("mutability", "readWrite")
    normalized.setdefault("returned", "default")
    normalized.setdefault("required", False)

    if normalized_type == "string" and "caseExact" not in normalized:
        normalized["caseExact"] = False

    sub_attributes = normalized.get("subAttributes")
    if normalized_type == "complex" and isinstance(sub_attributes, list):
        normalized["subAttributes"] = [
            normalize_attribute_definition(sub) for sub in sub_attributes
        ]

    return normalized


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
        attr = normalize_attribute_definition(attr)
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
            'dateTime': datetime,
            'datetime': datetime,
            'reference': str,
            'binary': str,
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

    SchemaResources[schema_uri] = {
        "id": schema_uri,
        "name": resource_name,
        "description": f"Schema definition for {resource_name}",
        "attributes": attributes,
        "meta": {
            "location": f"/Schemas/{schema_uri}",
            "resourceType": "Schema"
        },
        "schemas": [
            CORE_SCHEMA + ":Schema"
        ]
    }

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
                    attributes = [
                        normalize_attribute_definition(attr)
                        for attr in schema_data.get('attributes', [])
                    ]

                    Schemas[resource][id] = register_model(
                        f"{resource}_{name}", attributes
                    )
                    SchemaResources[id] = {
                        "id": id,
                        "name": schema_data.get("name", name),
                        "description": schema_data.get(
                            "description",
                            f"Schema definition for {name}"
                        ),
                        "attributes": attributes,
                        "meta": {
                            "location": f"/Schemas/{id}",
                            "resourceType": "Schema"
                        },
                        "schemas": [
                            CORE_SCHEMA + ":Schema"
                        ]
                    }

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

        attributes = [
            normalize_attribute_definition(attr)
            for attr in schema_data.get('attributes', [])
        ]

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
