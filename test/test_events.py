# test/test_events.py

import json
from unittest.mock import MagicMock, patch

import pytest

from events.builder import build_provisioning_event
from events.mapping import PROV_CREATE_NOTICE, PROV_DELETE, PROV_PATCH_NOTICE
from events.publisher import emit_group_event, emit_user_event, publish_provisioning_event
from schema import SCIM_PATCH_OP


@pytest.fixture
def push_env(monkeypatch):
    monkeypatch.setenv("SET_PUSH_URL", "https://receiver.test/scim/events")
    monkeypatch.setenv("SET_ISSUER", "https://scim.test")
    monkeypatch.delenv("AMQP", raising=False)


def test_provisioning_create_notice_shape():
    resource = {
        "id": "user-1",
        "userName": "alice",
        "externalId": "alice@example.com",
        "meta": {"location": "/Users/user-1", "resourceType": "User"},
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    }
    set_token = build_provisioning_event("create", "User", resource)
    assert set_token["iss"] == "scim"
    assert set_token["sub_id"]["format"] == "scim"
    assert set_token["sub_id"]["uri"] == "/Users/user-1"
    assert set_token["sub_id"]["externalId"] == "alice@example.com"
    event = set_token["events"][PROV_CREATE_NOTICE]
    assert "attributes" in event
    assert "userName" in event["attributes"]
    assert "data" not in event


def test_provisioning_patch_notice_attributes():
    resource = {
        "id": "group-1",
        "displayName": "Demo",
        "meta": {"location": "/Groups/group-1", "resourceType": "Group"},
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
    }
    operations = [
        MagicMock(path="members", op="add", value=[{"value": "user-1"}]),
    ]
    set_token = build_provisioning_event(
        "patch",
        "Group",
        resource,
        patch_operations=operations,
    )
    event = set_token["events"][PROV_PATCH_NOTICE]
    assert event["attributes"] == ["members"]


def test_provisioning_delete_empty_payload():
    resource = {
        "id": "user-1",
        "meta": {"location": "/Users/user-1"},
    }
    set_token = build_provisioning_event("delete", "User", resource)
    assert set_token["events"][PROV_DELETE] == {}


@patch("events.publisher.deliver_set_push", return_value=True)
def test_publish_provisioning_event_calls_push(mock_deliver, push_env):
    resource = {"id": "x", "meta": {"location": "/Users/x"}}
    assert publish_provisioning_event("create", "User", resource) is True
    mock_deliver.assert_called_once()
    set_token = mock_deliver.call_args[0][0]
    assert PROV_CREATE_NOTICE in set_token["events"]


@patch("events.publisher.deliver_set_push", return_value=True)
def test_create_user_emits_set(mock_deliver, test_app, push_env):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    response = test_app.post(
        "/Users",
        json={
            "userName": "set-test-user",
            "emails": [{"primary": True, "value": "set@test.example"}],
            "active": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    mock_deliver.assert_called_once()
    set_token = mock_deliver.call_args[0][0]
    assert PROV_CREATE_NOTICE in set_token["events"]


@patch("events.publisher.deliver_set_push", return_value=True)
def test_patch_group_members_emits_set(mock_deliver, test_app, push_env):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    user_resp = test_app.post(
        "/Users",
        json={
            "userName": "set-member",
            "emails": [{"primary": True, "value": "m@test.example"}],
            "active": True,
        },
        headers=headers,
    )
    user_id = user_resp.json()["id"]

    group_resp = test_app.post(
        "/Groups",
        json={"displayName": "set-group"},
        headers=headers,
    )
    group_id = group_resp.json()["id"]
    mock_deliver.reset_mock()

    patch_resp = test_app.patch(
        f"/Groups/{group_id}",
        json={
            "Operations": [{
                "op": "add",
                "path": "members",
                "value": [{"value": user_id}],
            }],
            "schemas": [SCIM_PATCH_OP],
        },
        headers=headers,
    )
    assert patch_resp.status_code == 200
    mock_deliver.assert_called_once()
    set_token = mock_deliver.call_args[0][0]
    assert PROV_PATCH_NOTICE in set_token["events"]
    assert "members" in set_token["events"][PROV_PATCH_NOTICE]["attributes"]


def test_security_events_in_service_provider_config(test_app):
    response = test_app.get("/ServiceProviderConfig")
    assert response.status_code == 200
    body = response.json()
    assert "securityEvents" in body
    assert body["securityEvents"]["asyncRequest"] == "none"
    assert "urn:ietf:params:scim:event:prov:delete" in body["securityEvents"]["eventUris"]
