# test/test_async_jobs_unit.py

from unittest.mock import MagicMock

from events.async_jobs import (
    AsyncJobRecord,
    _location_from_response,
    _sub_id_for_async_record,
    build_async_response_set,
)
from events.mapping import MISC_ASYNC_RESP


def test_location_from_response_prefers_header():
    response = MagicMock()
    response.headers = {"location": "/Users/from-header"}
    assert _location_from_response(response, None) == "/Users/from-header"


def test_location_from_response_falls_back_to_meta():
    response = MagicMock()
    response.headers = {}
    body = {"meta": {"location": "/Users/from-meta"}, "id": "u1"}
    assert _location_from_response(response, body) == "/Users/from-meta"


def test_sub_id_for_async_record_uses_resource_uri():
    record = AsyncJobRecord(
        txn="txn-1",
        method="POST",
        path="/Users",
        location="/Users/abc",
        response_body={
            "id": "abc",
            "externalId": "ext-1",
            "meta": {"location": "/Users/abc"},
        },
    )
    sub_id = _sub_id_for_async_record(record)
    assert sub_id["uri"] == "/Users/abc"
    assert sub_id["id"] == "abc"
    assert sub_id["externalId"] == "ext-1"


def test_build_async_response_set_includes_resource_location():
    record = AsyncJobRecord(
        txn="txn-2",
        method="POST",
        path="/Users",
        location="/Users/xyz",
        status="201",
        response_body={"id": "xyz", "meta": {"location": "/Users/xyz"}},
    )
    token = build_async_response_set(record, "txn-2")
    assert token["sub_id"]["uri"] == "/Users/xyz"
    event = token["events"][MISC_ASYNC_RESP]
    assert event["location"] == "/Users/xyz"
