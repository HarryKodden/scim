# import test_user.py

from schema import User, UserResource, ListResponse, CORE_SCHEMA_USER

import logging
logger = logging.getLogger(__name__)


def test_get_users(test_app):
    headers = {
      'x-api-key': "secret"
    }

    response = test_app.get("/Users", headers=headers)
    assert response.status_code == 200


def test_create_user(test_app):
    headers = {
      'x-api-key': "secret",
      'content-type': 'application/scim+json'
    }

    data = {
      "userName": "testuser",
      "emails": [
        {
          "primary": True,
          "value": "noboby@nowhere"
        }
      ],
      "active": True
    }

    response = test_app.post("/Users", json=data, headers=headers)
    assert response.status_code == 201
    user = UserResource(**response.json())

    response = test_app.get(
      "/Users?filter=userName eq \"testuser\"",
      headers=headers
    )
    assert response.status_code == 200  # OK !
    listresponse = ListResponse(**response.json())
    assert listresponse.totalResults == 1
    assert len(listresponse.Resources) == 1
    assert listresponse.Resources[0].get('id') == user.id

    response = test_app.post("/Users", json=data, headers=headers)
    assert response.status_code == 409  # Duplicate !

    response = test_app.delete(f"/Users/{user.id}", headers=headers)
    assert response.status_code == 204

    response = test_app.get(
      "/Users?filter=userName eq \"testuser\"",
      headers=headers
    )
    assert response.status_code == 200  # OK !
    listresponse = ListResponse(**response.json())
    assert listresponse.totalResults == 0
    assert len(listresponse.Resources) == 0


def test_update_user(test_app):
    headers = {
      'x-api-key': "secret",
      'content-type': 'application/scim+json'
    }

    data = {
      "userName": "testuser",
      "emails": [
        {
          "primary": True,
          "value": "noboby@nowhere"
        }
      ],
      "active": True
    }

    response = test_app.post("/Users", json=data, headers=headers)
    assert response.status_code == 201
    user = UserResource(**response.json())
    id = user.id

    response = test_app.get("/Users/foobar", headers=headers)
    assert response.status_code == 404

    response = test_app.get(f"/Users/{id}", headers=headers)
    assert response.status_code == 200

    user = User(**response.json())
    user.active = False

    response = test_app.put(
      "/Users/foobar",
      json=user.model_dump(by_alias=True, exclude_none=True),
      headers=headers
    )
    assert response.status_code == 409

    response = test_app.put(
      f"/Users/{id}",
      json=user.model_dump(by_alias=True, exclude_none=True),
      headers=headers
    )

    assert response.status_code == 200
    user = UserResource(**response.json())
    assert user.active is False

    response = test_app.post("/Users", json=data, headers=headers)
    assert response.status_code == 409

    data = {
      "operations": [{
          "op": "add",
          "path": "externalId",
          "value": "external-1"
      }],
      "schemas": [CORE_SCHEMA_USER]
    }
    response = test_app.patch(f"/Users/{id}", json=data, headers=headers)
    assert response.status_code == 200

    data = {
      "userName": "testuser-1",
      "emails": [
        {
          "primary": True,
          "value": "noboby@nowhere"
        }
      ],
      "externalId": "external-1",
      "active": True
    }
    response = test_app.post("/Users", json=data, headers=headers)
    assert response.status_code == 409

    response = test_app.delete(f"/Users/{id}", headers=headers)
    assert response.status_code == 204


def test_delete_user(test_app):
    headers = {
      'x-api-key': "secret",
      'content-type': 'application/scim+json'
    }

    data = {
      "userName": "testuser",
      "emails": [
        {
          "primary": True,
          "value": "noboby@nowhere"
        }
      ],
      "active": True
    }

    response = test_app.post("/Users", json=data, headers=headers)
    assert response.status_code == 201
    user = UserResource(**response.json())
    response = test_app.delete(f"/Users/{user.id}", headers=headers)
    assert response.status_code == 204
