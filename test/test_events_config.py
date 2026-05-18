# test/test_events_config.py

from events import DEFAULT_NOTICE_EVENT_URIS, publish_event
from events.builder import build_set_envelope, build_sub_id, new_jti
from events.config import load_event_config
from events.delivery.push import SET_CONTENT_TYPE


def test_load_event_config_defaults(monkeypatch):
    monkeypatch.delenv("SET_PUSH_URL", raising=False)
    monkeypatch.delenv("EVENT_MODE", raising=False)
    monkeypatch.delenv("ASYNC_REQUEST", raising=False)

    cfg = load_event_config()
    assert cfg.issuer == "scim"
    assert cfg.event_mode == "notice"
    assert cfg.async_request == "none"
    assert not cfg.push_enabled
    assert not cfg.signing_enabled
    assert not cfg.push_require_tls


def test_load_event_config_set_push(monkeypatch):
    monkeypatch.setenv("SET_ISSUER", "https://scim.example.com")
    monkeypatch.setenv("SET_PUSH_URL", "https://receiver.example.com/events")
    monkeypatch.setenv("SET_PUSH_TOKEN", "secret")
    monkeypatch.setenv("EVENT_MODE", "full")
    monkeypatch.setenv("ASYNC_REQUEST", "request")

    cfg = load_event_config()
    assert cfg.issuer == "https://scim.example.com"
    assert cfg.push_enabled
    assert cfg.event_mode == "full"
    assert cfg.async_request == "request"


def test_build_set_envelope():
    sub_id = build_sub_id(
        "/Users/abc",
        external_id="ext-1",
        resource_id="abc",
    )
    envelope = build_set_envelope(
        "urn:ietf:params:scim:event:prov:delete",
        {},
        sub_id,
    )
    assert envelope["sub_id"]["format"] == "scim"
    assert envelope["sub_id"]["uri"] == "/Users/abc"
    assert "jti" in envelope
    assert "iat" in envelope
    assert envelope["events"]["urn:ietf:params:scim:event:prov:delete"] == {}


def test_publish_event_without_push_returns_false(monkeypatch):
    monkeypatch.delenv("SET_PUSH_URL", raising=False)
    assert publish_event({"jti": new_jti()}) is False


def test_default_notice_event_uris():
    assert "urn:ietf:params:scim:event:prov:delete" in DEFAULT_NOTICE_EVENT_URIS


def test_set_content_type():
    assert SET_CONTENT_TYPE == "application/secevent+jwt"
