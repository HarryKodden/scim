# test/test_services.py

"""Coverage for services layer (users/groups) via bulk and direct calls."""

import uuid
from unittest.mock import patch

from schema import SCIM_BULK_REQUEST, SCIM_PATCH_OP
from services import groups as group_ops
from services import users as user_ops


def _headers():
    return {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }


def _user_data(user_name: str, *, external_id=None, email=None):
    data = {
        "userName": user_name,
        "active": True,
        "emails": [{"primary": True, "value": email or f"{user_name}@test.example"}],
    }
    if external_id is not None:
        data["externalId"] = external_id
    return data


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def test_create_user_validation_error():
    status, body, _ = user_ops.create_user(
        {"userName": 12345, "active": True},
        emit_events=False,
    )
    assert status == 422
    assert "Invalid User resource" in body["detail"]


def test_create_user_duplicate_external_id(test_app):
    ext_id = _uid("ext-dup")
    payload = _user_data(_uid("svc-ext-1"), external_id=ext_id)
    assert user_ops.create_user(payload, emit_events=False)[0] == 201
    status, body, _ = user_ops.create_user(
        _user_data(_uid("svc-ext-2"), external_id=ext_id),
        emit_events=False,
    )
    assert status == 409
    assert "externalId" in body["detail"]


def test_update_user_duplicate_username(test_app):
    name_a = _uid("svc-user-a")
    status1, body1, _ = user_ops.create_user(
        _user_data(name_a), emit_events=False
    )
    status2, body2, _ = user_ops.create_user(
        _user_data(_uid("svc-user-b")), emit_events=False
    )
    assert status1 == 201 and status2 == 201
    user_id = body2["id"]
    status, body, _ = user_ops.update_user(
        user_id,
        _user_data(name_a),
        emit_events=False,
    )
    assert status == 409
    assert "userName" in body["detail"]


def test_update_user_duplicate_external_id():
    ext_owner = _uid("ext-owner")
    user_ops.create_user(
        _user_data(_uid("svc-ext-owner"), external_id=ext_owner),
        emit_events=False,
    )
    _, body2, _ = user_ops.create_user(
        _user_data(_uid("svc-ext-other"), external_id=_uid("ext-other")),
        emit_events=False,
    )
    status, body, _ = user_ops.update_user(
        body2["id"],
        _user_data(body2["userName"], external_id=ext_owner),
        emit_events=False,
    )
    assert status == 409


def test_update_user_not_found():
    status, body, _ = user_ops.update_user(
        "00000000-0000-0000-0000-000000000099",
        _user_data("ghost"),
        emit_events=False,
    )
    assert status == 404


def test_patch_user_missing_patch_schema():
    _, body, _ = user_ops.create_user(
        _user_data(_uid("svc-patch-schema")), emit_events=False
    )
    status, err, _ = user_ops.patch_user(
        body["id"],
        {
            "schemas": ["urn:example:wrong:PatchOp"],
            "Operations": [{"op": "replace", "path": "active", "value": False}],
        },
        emit_events=False,
    )
    assert status == 400
    assert SCIM_PATCH_OP in err["detail"]


def test_patch_user_if_match_mismatch():
    _, body, _ = user_ops.create_user(
        _user_data(_uid("svc-patch-etag")), emit_events=False
    )
    status, err, _ = user_ops.patch_user(
        body["id"],
        {
            "schemas": [SCIM_PATCH_OP],
            "Operations": [{"op": "replace", "path": "active", "value": False}],
        },
        if_match='W/"stale"',
        emit_events=False,
    )
    assert status == 412


def test_patch_user_remove_missing_path():
    _, body, _ = user_ops.create_user(
        _user_data(_uid("svc-patch-bad")), emit_events=False
    )
    status, err, _ = user_ops.patch_user(
        body["id"],
        {
            "schemas": [SCIM_PATCH_OP],
            "Operations": [{"op": "remove", "path": "nonexistentAttribute"}],
        },
        emit_events=False,
    )
    assert status == 400
    assert "remove" in err["detail"].lower() or "non-existing" in err["detail"].lower()


@patch("services.users.emit_group_event")
@patch("services.users.emit_user_event")
def test_delete_user_removes_group_membership(_mock_user_evt, _mock_group_evt, test_app):
    _, user_body, _ = user_ops.create_user(
        _user_data(_uid("svc-del-member")), emit_events=False
    )
    user_id = user_body["id"]
    _, group_body, _ = group_ops.create_group(
        {"displayName": _uid("svc-del-group")},
        emit_events=False,
    )
    group_id = group_body["id"]
    group_ops.patch_group(
        group_id,
        {
            "schemas": [SCIM_PATCH_OP],
            "Operations": [{
                "op": "add",
                "path": "members",
                "value": [{"value": user_id}],
            }],
        },
        emit_events=False,
    )

    status, _, _ = user_ops.delete_user(user_id, emit_events=True)
    assert status == 204
    _mock_group_evt.assert_called()

    get_group = test_app.get(f"/Groups/{group_id}", headers=_headers())
    members = get_group.json().get("members") or []
    assert not any(m.get("value") == user_id for m in members)


def test_create_group_validation_error():
    status, body, _ = group_ops.create_group({}, emit_events=False)
    assert status == 422


def test_create_group_duplicate_external_id():
    ext_id = _uid("grp-ext")
    group_ops.create_group(
        {"displayName": _uid("grp-1"), "externalId": ext_id},
        emit_events=False,
    )
    status, body, _ = group_ops.create_group(
        {"displayName": _uid("grp-2"), "externalId": ext_id},
        emit_events=False,
    )
    assert status == 409


def test_update_group_not_found():
    status, body, _ = group_ops.update_group(
        "00000000-0000-0000-0000-000000000099",
        {"displayName": "missing"},
        emit_events=False,
    )
    assert status == 404


def test_update_group_if_match_mismatch():
    _, body, _ = group_ops.create_group(
        {"displayName": _uid("grp-etag")}, emit_events=False
    )
    status, err, _ = group_ops.update_group(
        body["id"],
        {"displayName": "grp-etag-renamed"},
        if_match='W/"stale"',
        emit_events=False,
    )
    assert status == 412


def test_patch_group_missing_patch_schema():
    _, body, _ = group_ops.create_group(
        {"displayName": _uid("grp-patch")}, emit_events=False
    )
    status, err, _ = group_ops.patch_group(
        body["id"],
        {
            "schemas": ["urn:example:wrong:PatchOp"],
            "Operations": [{
                "op": "replace",
                "path": "displayName",
                "value": "x",
            }],
        },
        emit_events=False,
    )
    assert status == 400


def test_delete_group_not_found():
    status, body, _ = group_ops.delete_group(
        "00000000-0000-0000-0000-000000000099",
        emit_events=False,
    )
    assert status == 404


@patch("services.users.emit_user_lifecycle_event")
@patch("services.users.emit_user_event")
def test_update_user_active_lifecycle(mock_user_evt, mock_lifecycle):
    user_name = _uid("svc-lifecycle")
    _, body, _ = user_ops.create_user(_user_data(user_name), emit_events=True)
    user_id = body["id"]
    status, _, _ = user_ops.update_user(
        user_id,
        _user_data(user_name),
        emit_events=True,
    )
    assert status == 200
    mock_lifecycle.assert_not_called()

    status, _, _ = user_ops.update_user(
        user_id,
        {**_user_data(user_name), "active": False},
        emit_events=True,
    )
    assert status == 200
    assert mock_lifecycle.called


def test_bulk_services_paths_via_http(test_app):
    """Exercise remaining bulk executor branches tied to services."""
    suffix = uuid.uuid4().hex[:8]
    response = test_app.post(
        "/Bulk",
        json={
            "schemas": [SCIM_BULK_REQUEST],
            "Operations": [
                {
                    "method": "POST",
                    "path": "/Users",
                    "bulkId": "u1",
                    "data": _user_data(
                        f"bulk-svc-put-{suffix}",
                        external_id=f"bulk-ext-{suffix}",
                    ),
                },
                {
                    "method": "PUT",
                    "path": "/Users/bulkId:u1",
                    "data": {
                        **_user_data(
                            f"bulk-svc-put-{suffix}",
                            external_id=f"bulk-ext-{suffix}",
                        ),
                        "active": False,
                    },
                },
                {
                    "method": "POST",
                    "path": "/Groups",
                    "bulkId": "g1",
                    "data": {
                        "displayName": f"bulk-svc-grp-{suffix}",
                        "externalId": f"bulk-grp-ext-{suffix}",
                    },
                },
                {
                    "method": "DELETE",
                    "path": "/Groups/bulkId:g1",
                },
            ],
        },
        headers=_headers(),
    )
    ops = response.json()["Operations"]
    assert ops[0]["status"] == "201"
    assert ops[1]["status"] == "200"
    assert ops[2]["status"] == "201"
    assert ops[3]["status"] == "204"
