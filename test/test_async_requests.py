# test/test_async_requests.py

from unittest.mock import patch

import pytest

from events.async_jobs import SET_TXN_HEADER, clear_async_results
from events.mapping import MISC_ASYNC_RESP, PROV_CREATE_NOTICE
from events.prefer import parse_wait_seconds, wants_respond_async


@pytest.fixture
def async_env(monkeypatch):
    monkeypatch.setenv("ASYNC_REQUEST", "request")
    monkeypatch.setenv("ASYNC_INLINE", "1")
    monkeypatch.setenv("SET_PUSH_URL", "https://receiver.test/scim/events")
    monkeypatch.setenv("SET_ISSUER", "https://scim.test")
    clear_async_results()
    yield
    clear_async_results()


def test_prefer_header_parsing():
    assert wants_respond_async("respond-async")
    assert wants_respond_async("return=representation, respond-async")
    assert not wants_respond_async("return=representation")
    assert parse_wait_seconds("respond-async, wait=5") == 5.0
    assert parse_wait_seconds("wait=2.5") == 2.5


@patch("events.async_jobs.deliver_set", return_value=True)
def test_async_post_returns_202_and_completion_set(mock_deliver, test_app, async_env):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
        "Prefer": "respond-async",
    }
    response = test_app.post(
        "/Users",
        json={
            "userName": "async-user",
            "emails": [{"primary": True, "value": "async@test.example"}],
            "active": True,
        },
        headers=headers,
    )
    assert response.status_code == 202
    assert response.content == b""
    txn = response.headers[SET_TXN_HEADER]
    assert txn
    assert response.headers.get("Preference-Applied") == "respond-async"
    assert response.headers.get("Location") == f"/Async/{txn}"

    assert mock_deliver.call_count >= 1
    async_set = None
    for call in mock_deliver.call_args_list:
        token = call[0][0]
        if MISC_ASYNC_RESP in token.get("events", {}):
            async_set = token
    assert async_set is not None
    assert async_set["txn"] == txn
    event = async_set["events"][MISC_ASYNC_RESP]
    assert event["method"] == "POST"
    assert event["status"] == "201"
    assert "response" in event

    result_resp = test_app.get(f"/Async/{txn}", headers={"x-api-key": "secret"})
    assert result_resp.status_code == 200
    result = result_resp.json()
    assert result["method"] == "POST"
    assert result["status"] == "201"


@patch("events.publisher.deliver_set", return_value=True)
def test_async_disabled_without_prefer(mock_deliver, test_app, async_env):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    response = test_app.post(
        "/Users",
        json={
            "userName": "sync-user",
            "emails": [{"primary": True, "value": "sync@test.example"}],
            "active": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    prov_calls = [
        c for c in mock_deliver.call_args_list
        if PROV_CREATE_NOTICE in c[0][0].get("events", {})
    ]
    assert len(prov_calls) == 1
    async_calls = [
        c for c in mock_deliver.call_args_list
        if MISC_ASYNC_RESP in c[0][0].get("events", {})
    ]
    assert len(async_calls) == 0


def test_async_result_requires_auth(test_app, async_env):
    response = test_app.get("/Async/does-not-exist")
    assert response.status_code == 401


def test_security_events_async_request(test_app, async_env):
    response = test_app.get("/ServiceProviderConfig")
    assert response.status_code == 200
    from scim_errors import SCIM_EVENTS_EXTENSION

    security = response.json()[SCIM_EVENTS_EXTENSION]
    assert security["asyncRequest"] == "request"
    assert MISC_ASYNC_RESP in security["eventUris"]
