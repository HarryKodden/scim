# test/test_feeds.py

import uuid
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
    feed_member = f"feed-member-{uuid.uuid4().hex[:8]}"
    user_resp = test_app.post(
        "/Users",
        json={
            "userName": feed_member,
            "active": True,
            "emails": [{"primary": True, "value": f"{feed_member}@test.example"}],
        },
        headers=headers,
    )
    user_id = user_resp.json()["id"]

    group_resp = test_app.post(
        "/Groups",
        json={"displayName": f"feed-group-{uuid.uuid4().hex[:8]}"},
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
    poll_user = f"poll-user-{uuid.uuid4().hex[:8]}"
    test_app.post(
        "/Users",
        json={
            "userName": poll_user,
            "active": True,
            "emails": [{"primary": True, "value": f"{poll_user}@test.example"}],
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


def test_poll_stream_unknown_feed_returns_404(test_app, feed_env, monkeypatch):
    monkeypatch.setenv("SET_GROUP_AS_FEED", "false")
    response = test_app.get(
        "/Events/Feeds/unknown-feed/Stream",
        headers={"x-api-key": "secret"},
    )
    assert response.status_code == 404


def test_poll_disabled_returns_501(test_app, monkeypatch):
    monkeypatch.setenv("SET_POLL_ENABLED", "false")
    response = test_app.get(
        "/Events/Feeds/default/Stream",
        headers={"x-api-key": "secret"},
    )
    assert response.status_code == 501


def test_get_feed_by_id(test_app, feed_env):
    response = test_app.get(
        "/Events/Feeds/default",
        headers={"x-api-key": "secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "default"
    assert body["poll"]["supported"] is True
    assert body["poll"]["stream"].endswith("/Events/Feeds/default/Stream")
    assert isinstance(body["members"], list)


def test_get_unknown_feed_returns_404(test_app, feed_env, monkeypatch):
    monkeypatch.setenv("SET_GROUP_AS_FEED", "false")
    response = test_app.get(
        "/Events/Feeds/no-such-feed",
        headers={"x-api-key": "secret"},
    )
    assert response.status_code == 404
    assert response.json()["schemas"] == [
        "urn:ietf:params:scim:api:messages:2.0:Error"
    ]


@patch("events.delivery.push.deliver_set_push", return_value=True)
def test_poll_stream_after_cursor(_mock_push, test_app, feed_env, push_env):
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    for idx in range(3):
        poll_user = f"poll-cursor-{idx}-{uuid.uuid4().hex[:6]}"
        test_app.post(
            "/Users",
            json={
                "userName": poll_user,
                "active": True,
                "emails": [{
                    "primary": True,
                    "value": f"{poll_user}@test.example",
                }],
            },
            headers=headers,
        )

    first = test_app.get(
        "/Events/Feeds/default/Stream",
        headers={"x-api-key": "secret"},
    )
    assert first.status_code == 200
    sets = first.json()["sets"]
    assert len(sets) >= 3
    first_jti = sets[0]["jti"]

    page = test_app.get(
        f"/Events/Feeds/default/Stream?after={first_jti}&limit=1",
        headers={"x-api-key": "secret"},
    )
    assert page.status_code == 200
    body = page.json()
    assert len(body["sets"]) == 1
    assert body["sets"][0]["jti"] != first_jti
    assert body["moreAvailable"] is True
