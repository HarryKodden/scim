# test/test_phase3.py

from unittest.mock import patch

import jwt
import pytest

from schema import SCIM_PATCH_OP

from events.builder import build_lifecycle_event, build_provisioning_event
from events.config import load_event_config
from events.mapping import (
    PROV_ACTIVATE,
    PROV_CREATE_FULL,
    PROV_DEACTIVATE,
    PROV_PATCH_NOTICE,
)
from events.signing import prepare_set_delivery_body
from versioning import detect_active_change, new_version


@pytest.fixture
def push_env(monkeypatch):
    monkeypatch.setenv("SET_PUSH_URL", "https://receiver.test/scim/events")
    monkeypatch.setenv("SET_ISSUER", "https://scim.test")


def test_new_version_format():
    version = new_version()
    assert version.startswith('W/"')
    assert version.endswith('"')


def test_provisioning_notice_includes_version():
    resource = {
        "id": "user-1",
        "userName": "alice",
        "meta": {
            "location": "/Users/user-1",
            "resourceType": "User",
            "version": 'W/"v1"',
        },
    }
    set_token = build_provisioning_event("patch", "User", resource)
    event = set_token["events"][PROV_PATCH_NOTICE]
    assert event["version"] == 'W/"v1"'


def test_full_mode_event_uri(monkeypatch):
    monkeypatch.setenv("EVENT_MODE", "full")
    resource = {
        "id": "user-1",
        "userName": "bob",
        "meta": {"location": "/Users/user-1"},
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    }
    cfg = load_event_config()
    set_token = build_provisioning_event("create", "User", resource, config=cfg)
    assert PROV_CREATE_FULL in set_token["events"]
    assert "data" in set_token["events"][PROV_CREATE_FULL]


def test_lifecycle_activate_event():
    resource = {
        "id": "user-1",
        "meta": {"location": "/Users/user-1", "version": 'W/"v2"'},
    }
    set_token = build_lifecycle_event("activate", resource)
    assert PROV_ACTIVATE in set_token["events"]
    assert set_token["events"][PROV_ACTIVATE]["version"] == 'W/"v2"'


def test_detect_active_change():
    before = type("U", (), {"active": True})()
    after = type("U", (), {"active": False})()
    assert detect_active_change(before, after) == "deactivate"
    assert detect_active_change(after, before) == "activate"
    assert detect_active_change(before, before) is None


def test_set_signing_produces_jwt(monkeypatch):
    signing_secret = "0123456789abcdef0123456789abcdef"  # 32 bytes for HS256
    monkeypatch.setenv("SET_SIGNING_SECRET", signing_secret)
    cfg = load_event_config()
    body, content_type = prepare_set_delivery_body({"iss": "scim", "jti": "x"}, cfg)
    assert content_type == "application/secevent+jwt"
    decoded = jwt.decode(body, signing_secret, algorithms=["HS256"])
    assert decoded["iss"] == "scim"


def test_push_url_tls_required(monkeypatch):
    monkeypatch.setenv("SET_PUSH_URL", "http://insecure.example/events")
    monkeypatch.setenv("SET_PUSH_REQUIRE_TLS", "true")
    with pytest.raises(ValueError, match="HTTPS"):
        load_event_config()


@patch("events.publisher.deliver_set", return_value=True)
def test_user_deactivate_emits_lifecycle_set(mock_deliver, test_app, push_env):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    create = test_app.post(
        "/Users",
        json={
            "userName": "lifecycle-user",
            "active": True,
            "emails": [{"primary": True, "value": "life@test.example"}],
        },
        headers=headers,
    )
    assert create.status_code == 201
    user_id = create.json()["id"]
    etag = create.headers.get("ETag") or create.json()["meta"]["version"]
    assert etag
    mock_deliver.reset_mock()

    patch_resp = test_app.patch(
        f"/Users/{user_id}",
        json={
            "schemas": [SCIM_PATCH_OP],
            "Operations": [{"op": "replace", "path": "active", "value": False}],
        },
        headers={**headers, "If-Match": etag},
    )
    assert patch_resp.status_code == 200
    lifecycle_calls = [
        c for c in mock_deliver.call_args_list
        if PROV_DEACTIVATE in c[0][0].get("events", {})
    ]
    assert len(lifecycle_calls) == 1


@patch("events.publisher.deliver_set", return_value=True)
def test_if_match_mismatch_returns_412(mock_deliver, test_app, push_env):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    create = test_app.post(
        "/Users",
        json={
            "userName": "etag-user",
            "active": True,
            "emails": [{"primary": True, "value": "etag@test.example"}],
        },
        headers=headers,
    )
    user_id = create.json()["id"]
    response = test_app.put(
        f"/Users/{user_id}",
        json={
            "userName": "etag-user",
            "active": True,
            "emails": [{"primary": True, "value": "etag@test.example"}],
        },
        headers={**headers, "If-Match": 'W/"stale-version"'},
    )
    assert response.status_code == 412


def test_get_user_returns_etag(test_app):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    create = test_app.post(
        "/Users",
        json={
            "userName": "etag-get-user",
            "active": True,
            "emails": [{"primary": True, "value": "get@test.example"}],
        },
        headers=headers,
    )
    user_id = create.json()["id"]
    get_resp = test_app.get(f"/Users/{user_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.headers.get("ETag", "").startswith('W/"')
    assert get_resp.json()["meta"]["version"] == get_resp.headers["ETag"]
