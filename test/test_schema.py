# import test_schema.py


from schema import Schemas
import logging


logger = logging.getLogger(__name__)

SCHEMA_RESOURCE_URN = "urn:ietf:params:scim:schemas:core:2.0:Schema"
ALLOWED_SCIM_ATTRIBUTE_TYPES = {
    "string",
    "boolean",
    "integer",
    "decimal",
    "dateTime",
    "reference",
    "complex",
    "binary",
}


def assert_valid_scim_attribute(attr):
    assert isinstance(attr, dict)
    attr_type = attr.get("type")
    assert attr_type in ALLOWED_SCIM_ATTRIBUTE_TYPES

    if attr_type == "string":
        assert "caseExact" in attr
        assert isinstance(attr["caseExact"], bool)

    if attr_type == "complex" and isinstance(attr.get("subAttributes"), list):
        for sub_attr in attr["subAttributes"]:
            assert_valid_scim_attribute(sub_attr)


def assert_is_scim_schema_resource(item):
    assert isinstance(item, dict)
    assert item.get("id")
    assert item.get("name")
    assert item.get("description") is not None
    assert isinstance(item.get("attributes"), list)
    assert isinstance(item.get("meta"), dict)
    assert item["meta"].get("resourceType") == "Schema"
    assert item["meta"].get("location")
    assert item.get("schemas") == [SCHEMA_RESOURCE_URN]
    for attr in item["attributes"]:
        assert_valid_scim_attribute(attr)


def test_get_schemas(test_app):
    response = test_app.get("/Schemas")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("schemas") == [
        "urn:ietf:params:scim:api:messages:2.0:ListResponse"
    ]
    assert isinstance(payload.get("Resources"), list)
    assert payload.get("totalResults") == len(payload.get("Resources"))

    schemas = {**Schemas['User'], **Schemas['Group']}
    resource_by_id = {item["id"]: item for item in payload["Resources"]}
    assert set(resource_by_id.keys()) == set(schemas.keys())
    for item in payload["Resources"]:
        assert_is_scim_schema_resource(item)

    for id in schemas.keys():
        response = test_app.get(f"/Schemas/{id}")
        assert response.status_code == 200
        assert_is_scim_schema_resource(response.json())


def test_get_invalid_schemas(test_app):
    response = test_app.get("Schemas/foobar")
    assert response.status_code == 404
