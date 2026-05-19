# test/test_push.py

from unittest.mock import MagicMock, patch

import pytest

from events.config import EventConfig, load_event_config
from events.delivery.push import deliver_set_push


def test_push_url_tls_required(monkeypatch):
    monkeypatch.setenv("SET_PUSH_URL", "http://insecure.example/events")
    monkeypatch.setenv("SET_PUSH_REQUIRE_TLS", "true")
    with pytest.raises(ValueError, match="HTTPS"):
        load_event_config()


def test_deliver_push_without_url():
    cfg = EventConfig(
        issuer="scim",
        audience=None,
        push_url=None,
        push_token=None,
        event_mode="notice",
        async_request="none",
        signing_secret=None,
        signing_algorithm="HS256",
        push_require_tls=False,
        poll_enabled=False,
    )
    assert deliver_set_push({"jti": "x"}, cfg) is False


@patch("events.delivery.push.time.sleep")
@patch("events.delivery.push.httpx.Client")
def test_deliver_push_client_error_no_retry(mock_client_cls, _mock_sleep):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "bad request"
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    cfg = EventConfig(
        issuer="scim",
        audience=None,
        push_url="https://receiver.test/events",
        push_token=None,
        event_mode="notice",
        async_request="none",
        signing_secret=None,
        signing_algorithm="HS256",
        push_require_tls=False,
        poll_enabled=False,
    )
    assert deliver_set_push({"jti": "push-4xx"}, cfg) is False
    assert mock_client.post.call_count == 1


@patch("events.delivery.push.time.sleep")
@patch("events.delivery.push.httpx.Client")
def test_deliver_push_server_error_retries_then_fails(mock_client_cls, _mock_sleep):
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "unavailable"
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    cfg = EventConfig(
        issuer="scim",
        audience=None,
        push_url="https://receiver.test/events",
        push_token="tok",
        event_mode="notice",
        async_request="none",
        signing_secret=None,
        signing_algorithm="HS256",
        push_require_tls=False,
        poll_enabled=False,
    )
    assert deliver_set_push({"jti": "push-5xx"}, cfg) is False
    assert mock_client.post.call_count == 3


@patch("events.delivery.push.time.sleep")
@patch("events.delivery.push.httpx.Client")
def test_deliver_push_network_error_retries(mock_client_cls, _mock_sleep):
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.side_effect = ConnectionError("connection refused")
    mock_client_cls.return_value = mock_client

    cfg = EventConfig(
        issuer="scim",
        audience=None,
        push_url="https://receiver.test/events",
        push_token=None,
        event_mode="notice",
        async_request="none",
        signing_secret=None,
        signing_algorithm="HS256",
        push_require_tls=False,
        poll_enabled=False,
    )
    assert deliver_set_push({"jti": "push-net"}, cfg) is False
    assert mock_client.post.call_count == 3


@patch("events.delivery.push.httpx.Client")
def test_deliver_push_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    cfg = EventConfig(
        issuer="scim",
        audience=None,
        push_url="https://receiver.test/events",
        push_token=None,
        event_mode="notice",
        async_request="none",
        signing_secret=None,
        signing_algorithm="HS256",
        push_require_tls=False,
        poll_enabled=False,
    )
    assert deliver_set_push({"jti": "push-ok"}, cfg) is True
