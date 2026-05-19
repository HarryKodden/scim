# test/test_feeds.py

from unittest.mock import patch

import pytest

from events.delivery.poll import clear_poll_streams
from events.feed_registry import clear_feed_registry, get_members
from events.mapping import FEED_ADD, FEED_REMOVE
from schema import SCIM_PATCH_OP


@pytest.fixture
def feed_env(monkeypatch):
    monkeypatch.setenv("SET_FEEDS_ENABLED", "true")
    monkeypatch.setenv("SET_GROUP_AS_FEED", "true")
    monkeypatch.setenv("SET_POLL_ENABLED", "true")
    monkeypatch.setenv("SET_ISSUER", "https://scim.test")
    clear_feed_registry()
    clear_poll_streams()
    yield
    clear_feed_registry()
    clear_poll_streams()


@pytest.fixture
def push_env(monkeypatch):
    monkeypatch.setenv("SET_PUSH_URL", "https://receiver.test/scim/events")
    monkeypatch.setenv("SET_ISSUER", "https://scim.test")


def test_list_feeds(test_app, feed_env):
    response = test_app.get(
        "/Events/Feeds",
        headers={"x-api-key": "secret"},
    )
    assert response.status_code == 200
    resources = response.json()["Resources"]
    assert any(f["id"] == "default" for f in resources)


def test_security_events_includes_feed_uris(test_app, feed_env):
    response = test_app.get("/ServiceProviderConfig")
    from scim_errors import SCIM_EVENTS_EXTENSION

    security = response.json()[SCIM_EVENTS_EXTENSION]
    assert FEED_ADD in security["eventUris"]
    assert FEED_REMOVE in security["eventUris"]
    assert "feeds" in security
    assert len(security["feeds"]) >= 1


@patch("events.feed_events.deliver_set", return_value=True)
def test_group_member_add_emits_feed_add(mock_deliver, test_app, feed_env, push_env):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    user_resp = test_app.post(
        "/Users",
        json={
            "userName": "feed-member",
            "active": True,
            "emails": [{"primary": True, "value": "feed@test.example"}],
        },
        headers=headers,
    )
    user_id = user_resp.json()["id"]

    group_resp = test_app.post(
        "/Groups",
        json={"displayName": "feed-group"},
        headers=headers,
    )
    group_id = group_resp.json()["id"]
    mock_deliver.reset_mock()

    patch_resp = test_app.patch(
        f"/Groups/{group_id}",
        json={
            "schemas": [SCIM_PATCH_OP],
            "Operations": [{
                "op": "add",
                "path": "members",
                "value": [{"value": user_id}],
            }],
        },
        headers=headers,
    )
    assert patch_resp.status_code == 200

    feed_calls = [
        c for c in mock_deliver.call_args_list
        if FEED_ADD in c[0][0].get("events", {})
    ]
    assert len(feed_calls) == 1
    token = feed_calls[0][0][0]
    assert token["events"][FEED_ADD] == {}
    assert any(group_id in str(a) for a in token.get("aud", []))
    assert f"/Users/{user_id}" in get_members(group_id)


@patch("events.delivery.push.deliver_set_push", return_value=True)
def test_poll_stream_returns_stored_sets(_mock_push, test_app, feed_env, push_env):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    test_app.post(
        "/Users",
        json={
            "userName": "poll-user",
            "active": True,
            "emails": [{"primary": True, "value": "poll@test.example"}],
        },
        headers=headers,
    )

    stream = test_app.get(
        "/Events/Feeds/default/Stream",
        headers={"x-api-key": "secret"},
    )
    assert stream.status_code == 200
    body = stream.json()
    assert body["moreAvailable"] is False
    assert len(body["sets"]) >= 1
    assert body["sets"][0]["events"]


def test_poll_disabled_returns_501(test_app, monkeypatch):
    monkeypatch.setenv("SET_POLL_ENABLED", "false")
    response = test_app.get(
        "/Events/Feeds/default/Stream",
        headers={"x-api-key": "secret"},
    )
    assert response.status_code == 501
