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
    body = response.json()
    assert body["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:Error"]
    assert body["status"] == "404"


def test_group_schema_members_ref_attribute(test_app):
    group_schema_id = "urn:ietf:params:scim:schemas:core:2.0:Group"
    response = test_app.get(f"/Schemas/{group_schema_id}")
    assert response.status_code == 200
    members = next(
        a for a in response.json()["attributes"] if a["name"] == "members"
    )
    ref_attr = next(
        s for s in members["subAttributes"] if s["name"] == "$ref"
    )
    assert ref_attr["type"] == "reference"
    assert "alias" not in ref_attr


def test_openapi_nested_user_models_are_not_accumulated(test_app):
    """Nested SCIM models must not share a mutable field registry (Swagger hang)."""
    schema = test_app.app.openapi()
    components = schema["components"]["schemas"]

    assert set(components["User_name"]["properties"]) == {
        "familyName",
        "givenName",
    }
    assert set(components["User_emails"]["properties"]) == {
        "value",
        "type",
    }
    assert set(components["User_x509Certificates"]["properties"]) == {
        "value",
        "type",
    }

    post = schema["paths"]["/Users"]["post"]
    request_body = post["requestBody"]["content"]["application/json"]
    request_schema = request_body["schema"]
    assert "$ref" in request_schema
    examples = request_schema.get("examples") or request_body.get("examples", {})
    assert set(examples.keys()) == {"default"}
    assert "value" in examples["default"]

    assert len(str(schema).encode("utf-8")) < 30_000
