# test/test_poll_unit.py

"""Unit tests for poll delivery helpers."""

import pytest

from events.delivery.poll import (
    _feed_ids_from_aud,
    _max_events,
    append_set_to_feed,
    clear_poll_streams,
    poll_enabled,
    poll_feed,
    store_set_for_poll,
)


@pytest.fixture(autouse=True)
def reset_poll_streams():
    clear_poll_streams()
    yield
    clear_poll_streams()


def test_poll_enabled_false_by_default(monkeypatch):
    monkeypatch.delenv("SET_POLL_ENABLED", raising=False)
    assert poll_enabled() is False


def test_poll_enabled_true(monkeypatch):
    monkeypatch.setenv("SET_POLL_ENABLED", "true")
    assert poll_enabled() is True


def test_max_events_invalid_env_defaults(monkeypatch):
    monkeypatch.setenv("SET_POLL_MAX_EVENTS", "not-a-number")
    assert _max_events() == 10000


def test_store_skipped_when_poll_disabled(monkeypatch):
    monkeypatch.delenv("SET_POLL_ENABLED", raising=False)
    store_set_for_poll({"jti": "j1", "aud": "https://scim.test/Events/Feeds/default"})
    sets, more = poll_feed("default")
    assert sets == []
    assert more is False


def test_feed_ids_from_aud_defaults(monkeypatch):
    monkeypatch.setenv("SET_POLL_ENABLED", "true")
    assert _feed_ids_from_aud({}) == ["default"]


def test_feed_ids_from_aud_string_uri(monkeypatch):
    monkeypatch.setenv("SET_POLL_ENABLED", "true")
    aud = "https://scim.test/Events/Feeds/custom-feed/extra"
    assert _feed_ids_from_aud({"aud": aud}) == ["custom-feed"]


def test_feed_ids_from_aud_list_uris(monkeypatch):
    monkeypatch.setenv("SET_POLL_ENABLED", "true")
    aud = [
        "https://scim.test/Events/Feeds/feed-a",
        "https://other/Events/Feeds/feed-b",
    ]
    assert _feed_ids_from_aud({"aud": aud}) == ["feed-a", "feed-b"]


def test_feed_ids_from_aud_fallback_to_known_feed(monkeypatch):
    monkeypatch.setenv("SET_POLL_ENABLED", "true")
    monkeypatch.setenv("SET_FEEDS", "alt-feed")
    assert _feed_ids_from_aud({"aud": "https://issuer.example/no-feed-marker"}) == [
        "alt-feed"
    ]


def test_append_and_poll_with_cursor(monkeypatch):
    monkeypatch.setenv("SET_POLL_ENABLED", "true")
    for idx in range(3):
        append_set_to_feed("default", {"jti": f"jti-{idx}", "events": {}})
    all_sets, _ = poll_feed("default")
    assert len(all_sets) == 3
    page, more = poll_feed("default", after_jti="jti-0", limit=1)
    assert len(page) == 1
    assert page[0]["jti"] == "jti-1"
    assert more is True
