# test/test_bulk.py

from unittest.mock import patch

import pytest

from events.async_jobs import clear_async_results
from events.mapping import MISC_ASYNC_RESP
from schema import SCIM_BULK_REQUEST, SCIM_BULK_RESPONSE, SCIM_PATCH_OP


@pytest.fixture
def push_env(monkeypatch):
    monkeypatch.setenv("SET_PUSH_URL", "https://receiver.test/scim/events")
    monkeypatch.setenv("SET_ISSUER", "https://scim.test")


@pytest.fixture
def async_bulk_env(monkeypatch):
    monkeypatch.setenv("ASYNC_REQUEST", "request")
    monkeypatch.setenv("ASYNC_INLINE", "1")
    monkeypatch.setenv("SET_PUSH_URL", "https://receiver.test/scim/events")
    clear_async_results()
    yield
    clear_async_results()


def _bulk_headers(*, respond_async: bool = False):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    if respond_async:
        headers["Prefer"] = "respond-async"
    return headers


def test_bulk_create_user(test_app):
    response = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "Operations": [{
                "method": "POST",
                "path": "/Users",
                "bulkId": "newuser",
                "data": {
                    "userName": "bulk-create-1",
                    "active": True,
                    "emails": [{"primary": True, "value": "bulk1@test.example"}],
                },
            }],
        },
        headers=_bulk_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert SCIM_BULK_RESPONSE in body["schemas"]
    assert body["Operations"][0]["status"] == "201"
    assert body["Operations"][0]["bulkId"] == "newuser"
    assert body["Operations"][0]["response"]["userName"] == "bulk-create-1"


def test_bulk_patch_by_bulk_id(test_app):
    response = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "Operations": [
                {
                    "method": "POST",
                    "path": "/Users",
                    "bulkId": "u1",
                    "data": {
                        "userName": "bulk-patch-target",
                        "active": True,
                        "emails": [{"primary": True, "value": "bulkpatch@test.example"}],
                    },
                },
                {
                    "method": "PATCH",
                    "path": "/Users/bulkId:u1",
                    "data": {
                        "schemas": [SCIM_PATCH_OP],
                        "Operations": [{
                            "op": "replace",
                            "path": "displayName",
                            "value": "Bulk Patched",
                        }],
                    },
                },
            ],
        },
        headers=_bulk_headers(),
    )
    assert response.status_code == 200
    ops = response.json()["Operations"]
    assert ops[0]["status"] == "201"
    assert ops[1]["status"] == "200"
    assert ops[1]["response"]["displayName"] == "Bulk Patched"


def test_bulk_fail_on_errors(test_app):
    response = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "failOnErrors": 1,
            "Operations": [
                {
                    "method": "POST",
                    "path": "/Users",
                    "data": {
                        "userName": "bulk-fail-1",
                        "active": True,
                        "emails": [{"primary": True, "value": "fail1@test.example"}],
                    },
                },
                {
                    "method": "PATCH",
                    "path": "/Users/nonexistent-id-xyz",
                    "data": {
                        "schemas": [SCIM_PATCH_OP],
                        "Operations": [{"op": "replace", "path": "active", "value": False}],
                    },
                },
                {
                    "method": "POST",
                    "path": "/Users",
                    "data": {
                        "userName": "bulk-fail-2",
                        "active": True,
                        "emails": [{"primary": True, "value": "fail2@test.example"}],
                    },
                },
            ],
        },
        headers=_bulk_headers(),
    )
    assert response.status_code == 200
    ops = response.json()["Operations"]
    assert len(ops) == 2
    assert ops[0]["status"] == "201"
    assert ops[1]["status"] == "404"


def test_service_provider_config_bulk_supported(test_app):
    response = test_app.get("/ServiceProviderConfig")
    assert response.json()["bulk"]["supported"] is True


@patch("events.async_jobs.deliver_set", return_value=True)
def test_async_bulk_emits_per_operation_txn(mock_deliver, test_app, async_bulk_env):
    response = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "Operations": [
                {
                    "method": "POST",
                    "path": "/Users",
                    "data": {
                        "userName": "async-bulk-user-1",
                        "active": True,
                        "emails": [{"primary": True, "value": "ab1@test.example"}],
                    },
                },
                {
                    "method": "POST",
                    "path": "/Users",
                    "data": {
                        "userName": "async-bulk-user-2",
                        "active": True,
                        "emails": [{"primary": True, "value": "ab2@test.example"}],
                    },
                },
            ],
        },
        headers=_bulk_headers(respond_async=True),
    )
    assert response.status_code == 202
    base_txn = response.headers.get("Set-Txn")
    assert base_txn

    async_txns = [
        call[0][0].get("txn")
        for call in mock_deliver.call_args_list
        if MISC_ASYNC_RESP in call[0][0].get("events", {})
    ]
    assert f"{base_txn}:0" in async_txns
    assert f"{base_txn}:1" in async_txns

    for call in mock_deliver.call_args_list:
        token = call[0][0]
        if MISC_ASYNC_RESP not in token.get("events", {}):
            continue
        event = token["events"][MISC_ASYNC_RESP]
        assert event["status"] == "201"
        assert token["txn"].startswith(f"{base_txn}:")

    bulk_result = test_app.get(
        f"/Async/{base_txn}",
        headers={"x-api-key": "secret"},
    )
    assert bulk_result.status_code == 200
    assert SCIM_BULK_RESPONSE in bulk_result.json()["schemas"]
    assert len(bulk_result.json()["Operations"]) == 2


def _user_payload(user_name: str, email: str):
    return {
        "userName": user_name,
        "active": True,
        "emails": [{"primary": True, "value": email}],
    }


def test_bulk_put_and_delete_user(test_app):
    create = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "Operations": [
                {
                    "method": "POST",
                    "path": "/Users",
                    "bulkId": "u1",
                    "data": _user_payload("bulk-put-user", "bulkput@test.example"),
                },
                {
                    "method": "PUT",
                    "path": "/Users/bulkId:u1",
                    "data": _user_payload("bulk-put-user", "bulkput@test.example"),
                },
                {
                    "method": "DELETE",
                    "path": "/Users/bulkId:u1",
                },
            ],
        },
        headers=_bulk_headers(),
    )
    assert create.status_code == 200
    ops = create.json()["Operations"]
    assert ops[0]["status"] == "201"
    assert ops[1]["status"] == "200"
    assert ops[2]["status"] == "204"
    assert test_app.get(
        f"/Users/{ops[0]['response']['id']}",
        headers={"x-api-key": "secret"},
    ).status_code == 404


def test_bulk_put_user_if_match_mismatch(test_app):
    response = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "Operations": [
                {
                    "method": "POST",
                    "path": "/Users",
                    "bulkId": "u1",
                    "data": _user_payload("bulk-etag-user", "bulketag@test.example"),
                },
                {
                    "method": "PUT",
                    "path": "/Users/bulkId:u1",
                    "version": 'W/"stale"',
                    "data": _user_payload("bulk-etag-user", "bulketag@test.example"),
                },
            ],
        },
        headers=_bulk_headers(),
    )
    ops = response.json()["Operations"]
    assert ops[0]["status"] == "201"
    assert ops[1]["status"] == "412"


def test_bulk_group_crud(test_app):
    response = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "Operations": [
                {
                    "method": "POST",
                    "path": "/Groups",
                    "bulkId": "g1",
                    "data": {"displayName": "bulk-group-crud"},
                },
                {
                    "method": "PATCH",
                    "path": "/Groups/bulkId:g1",
                    "data": {
                        "schemas": [SCIM_PATCH_OP],
                        "Operations": [{
                            "op": "replace",
                            "path": "displayName",
                            "value": "bulk-group-renamed",
                        }],
                    },
                },
                {
                    "method": "PUT",
                    "path": "/Groups/bulkId:g1",
                    "data": {"displayName": "bulk-group-final"},
                },
                {
                    "method": "DELETE",
                    "path": "/Groups/bulkId:g1",
                },
            ],
        },
        headers=_bulk_headers(),
    )
    ops = response.json()["Operations"]
    assert ops[0]["status"] == "201"
    assert ops[1]["status"] == "200"
    assert ops[1]["response"]["displayName"] == "bulk-group-renamed"
    assert ops[2]["status"] == "200"
    assert ops[3]["status"] == "204"


def test_bulk_unknown_path_returns_404(test_app):
    response = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "Operations": [{
                "method": "POST",
                "path": "/Widgets",
                "data": {"displayName": "nope"},
            }],
        },
        headers=_bulk_headers(),
    )
    op = response.json()["Operations"][0]
    assert op["status"] == "404"
    assert "Unknown path" in op["response"]["detail"]


def test_bulk_method_not_allowed_returns_405(test_app):
    response = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "Operations": [{
                "method": "GET",
                "path": "/Users",
            }],
        },
        headers=_bulk_headers(),
    )
    op = response.json()["Operations"][0]
    assert op["status"] == "405"


def test_bulk_unknown_bulk_id_returns_400(test_app):
    response = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "Operations": [{
                "method": "PATCH",
                "path": "/Users/bulkId:missing",
                "data": {
                    "schemas": [SCIM_PATCH_OP],
                    "Operations": [{"op": "replace", "path": "active", "value": False}],
                },
            }],
        },
        headers=_bulk_headers(),
    )
    op = response.json()["Operations"][0]
    assert op["status"] == "400"
    assert "bulkId" in op["response"]["detail"]
