# import test_user.py

from schema import UserResource, ListResponse

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

    response = test_app.get(f"/Users/{user.id}", headers=headers)
    assert response.status_code == 200

    response = test_app.post("/Users", json=data, headers=headers)
    assert response.status_code == 409

    response = test_app.delete(f"/Users/{user.id}", headers=headers)
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
