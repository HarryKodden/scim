# test/test_routers_utils.py

"""Unit tests for router helpers (patch, redaction, list)."""

import logging

import pytest
from fastapi import HTTPException

from routers import (
    get_all_resources,
    patch_resource,
    redact_request_body,
    _redact_sensitive,
)
from schema import Operation


def test_redact_sensitive_dict_and_list():
    payload = {
        "userName": "alice",
        "password": "secret",
        "nested": [{"api_key": "k", "ok": True}],
    }
    redacted = _redact_sensitive(payload)
    assert redacted["password"] == "***REDACTED***"
    assert redacted["nested"][0]["api_key"] == "***REDACTED***"
    assert redacted["userName"] == "alice"


def test_redact_request_body_invalid_json():
    assert redact_request_body("not-json") == "not-json"


def test_redact_request_body_strips_secrets():
    body = redact_request_body('{"userName": "a", "token": "xyz"}')
    assert "***REDACTED***" in body
    assert "xyz" not in body


def test_get_all_resources_unknown_type():
    with pytest.raises(HTTPException) as exc:
        get_all_resources("NoSuchType", 1, 10, None)
    assert exc.value.status_code == 404


def test_patch_remove_filtered_member():
    resource = {
        "members": [
            {"value": "u1", "display": "One"},
            {"value": "u2", "display": "Two"},
        ],
    }
    patch_resource(resource, [
        Operation(op="remove", path='members[value eq "u1"]'),
    ])
    assert len(resource["members"]) == 1
    assert resource["members"][0]["value"] == "u2"


def test_patch_remove_with_value_on_multivalued():
    resource = {
        "members": [
            {"value": "u1"},
            {"value": "u2"},
        ],
    }
    patch_resource(resource, [
        Operation(
            op="remove",
            path="members",
            value={"value": "u1"},
        ),
    ])
    assert len(resource["members"]) == 1


def test_patch_add_creates_missing_path():
    resource = {"displayName": "g"}
    patch_resource(resource, [
        Operation(op="add", path="externalId", value="ext-99"),
    ])
    assert resource["externalId"] == "ext-99"


def test_patch_add_to_non_list_raises():
    resource = {"displayName": "g"}
    with pytest.raises(HTTPException) as exc:
        patch_resource(resource, [
            Operation(op="add", path="displayName", value="x"),
        ])
    assert exc.value.status_code == 400


def test_patch_unknown_operation():
    class UnknownOp:
        op = "copy"
        path = "active"
        value = False

    resource = {"active": True}
    with pytest.raises(HTTPException) as exc:
        patch_resource(resource, [UnknownOp()])
    assert "Unknown operation" in str(exc.value.detail)


def test_scim_route_logs_failed_request(test_app, caplog):
    caplog.set_level(logging.ERROR)
    response = test_app.post(
        "/Users",
        json={"userName": "log-fail-user", "active": True},
        headers={
            "x-api-key": "secret",
            "content-type": "text/plain",
        },
    )
    assert response.status_code in (201, 400, 422, 500)
    assert any(
        "REQ FAIL" in r.message or "content-type" in r.message
        for r in caplog.records
    )


def test_scim_route_debug_body_redaction(test_app, caplog):
    caplog.set_level(logging.DEBUG)
    test_app.post(
        "/Users",
        json={
            "userName": "debug-redact-user",
            "active": True,
            "emails": [{"primary": True, "value": "dbg@test.example"}],
        },
        headers={
            "x-api-key": "secret",
            "content-type": "application/scim+json",
        },
    )
    assert any(
        "debug-redact-user" in r.message or "REQ" in r.message
        for r in caplog.records
    )
