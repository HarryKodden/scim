# import test_group.py

from schema import UserResource, GroupResource, Group, SCIM_PATCH_OP

import logging
logger = logging.getLogger(__name__)


def test_get_groups(test_app):
    headers = {
      'x-api-key': "secret"
    }

    response = test_app.get("/Groups", headers=headers)
    assert response.status_code == 200


def test_get_groups_not_exists(test_app):
    headers = {
      'x-api-key': "secret"
    }

    response = test_app.get("/Groups/xxx", headers=headers)
    assert response.status_code == 404


def test_create_group_non_exisiting_member(test_app):
    headers = {
      'x-api-key': "secret",
      'content-type': 'application/scim+json'
    }

    data = {
      "displayName": "testgroup",
      "members": [
        {
          "display": "John Doe",
          "value": "john"
        }
      ]
    }

    response = test_app.post("/Groups", json=data, headers=headers)
    assert response.status_code == 404


def test_create_group(test_app):
    headers = {
      'x-api-key': "secret",
      'content-type': 'application/scim+json'
    }

    data = {
      "displayName": "testgroup",
      "externalId": "external_id"
    }

    response = test_app.post("/Groups", json=data, headers=headers)
    assert response.status_code == 201


def test_duplicate_group(test_app):
    headers = {
      'x-api-key': "secret",
      'content-type': 'application/scim+json'
    }

    response = test_app.post(
      "/Groups",
      json={
        "displayName": "testgroup123",
        "externalId": "124"
      },
      headers=headers
    )
    assert response.status_code == 201
    group = GroupResource(**response.json())

    data = {
      "displayName": "testgroup456",
      "externalId": "124"
    }
    response = test_app.post("/Groups", json=data, headers=headers)
    assert response.status_code == 409

    response = test_app.delete(f"/Groups/{group.id}", headers=headers)
    assert response.status_code == 204


def test_group_updates(test_app):
    headers = {
      'x-api-key': "secret",
      'content-type': 'application/scim+json'
    }

    response = test_app.post(
      "/Users",
      json={
        "userName": "testmember",
        "emails": [
          {
            "primary": True,
            "value": "noboby@nowhere"
          }
        ],
        "active": True
      },
      headers=headers
    )
    assert response.status_code == 201
    user = UserResource(**response.json())

    response = test_app.post(
      "/Groups",
      json={
        "displayName": "test_group_updates",
        "members": [
          {
            "display": user.displayName,
            "value": user.id
          }
        ]
      },
      headers=headers
    )
    assert response.status_code == 201
    group = GroupResource(**response.json())

    response = test_app.get(
      f"/Groups/{group.id}",
      headers=headers
    )
    assert response.status_code == 200
    group = GroupResource(**response.json())

    assert len(group.members) == 1

    response = test_app.patch(
      f"/Groups/{group.id}",
      json={
        "Operations": [{
            "op": "remove",
            "path": "members"
        }],
        "schemas": [SCIM_PATCH_OP]
      },
      headers=headers
    )
    assert response.status_code == 200

    response = test_app.get(
      f"/Groups/{group.id}",
      headers=headers
    )
    assert response.status_code == 200
    group = GroupResource(**response.json())

    assert not group.members or len(group.members) == 0

    response = test_app.patch(
      f"/Groups/{group.id}",
      json={
        "Operations": [{
            "op": "add",
            "path": "members",
            "value": [
              {
                "value": user.id
              }
            ]
        }],
        "schemas": [SCIM_PATCH_OP]
      },
      headers=headers
    )
    assert response.status_code == 200

    response = test_app.get(
      f"/Groups/{group.id}",
      headers=headers
    )
    assert response.status_code == 200
    group = GroupResource(**response.json())

    assert len(group.members) == 1

    response = test_app.patch(
      f"/Groups/{group.id}",
      json={
        "Operations": [{
            "op": "add",
            "path": "externalId",
            "value": "external-1"
        }],
        "schemas": [SCIM_PATCH_OP]
      },
      headers=headers
    )
    assert response.status_code == 200

    data = {
      "displayName": "test_group_with_duplicate_externalid",
      "members": [],
      "externalId": "external-1"
    }

    response = test_app.post(
      "/Groups",
      json=data,
      headers=headers
    )
    assert response.status_code == 409


def test_update_group(test_app):
    headers = {
      'x-api-key': "secret",
      'content-type': 'application/scim+json'
    }

    response = test_app.post(
      "/Groups",
      json={
        "displayName": "test_update_group"
      },
      headers=headers
    )
    assert response.status_code == 201
    group = GroupResource(**response.json())

    response = test_app.get(
      f"/Groups/{group.id}",
      headers=headers
    )
    assert response.status_code == 200

    data = Group(**response.json())
    data.displayName = 'testgroup2'

    response = test_app.put(
      "/Groups/foobar",
      json=data.model_dump(by_alias=True, exclude_none=True),
      headers=headers
    )
    assert response.status_code == 404

    response = test_app.put(
      f"/Groups/{group.id}",
      json=data.model_dump(by_alias=True, exclude_none=True),
      headers=headers
    )
    assert response.status_code == 200


def test_delete_group(test_app):
    headers = {
      'x-api-key': 'secret',
      'content-type': 'application/scim+json'
    }

    response = test_app.post(
      "/Groups",
      json={
        "displayName": "test_update_group"
      },
      headers=headers
    )
    assert response.status_code == 201
    group = GroupResource(**response.json())
    response = test_app.delete(
      f"/Groups/{group.id}",
      headers=headers
    )
    assert response.status_code == 204


# PUT group that does not exist
# PATH group that does not exists
# PATCH group raise exception
