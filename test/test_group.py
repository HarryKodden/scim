# import test_group.py

from schema import GroupResource

import logging
logger = logging.getLogger(__name__)


def test_get_groups(test_app):
    headers = {
      'x-api-key': "secret"
    }

    response = test_app.get("/Groups", headers=headers)
    assert response.status_code == 200


def test_create_group(test_app):
    headers = {
      'x-api-key': "secret"
    }

    data = {
      "displayName": "testgroup"
    }

    response = test_app.post("/Groups", json=data, headers=headers)
    assert response.status_code == 201


def test_duplicate_group(test_app):
    headers = {
      'x-api-key': "secret"
    }

    data = {
      "displayName": "testgroup123",
      "externalId": "123"
    }

    response = test_app.post("/Groups", json=data, headers=headers)
    assert response.status_code == 201
    group = GroupResource(**response.json())

    data = {
      "displayName": "testgroup456",
      "externalId": "123"
    }
    response = test_app.post("/Groups", json=data, headers=headers)
    assert response.status_code == 409

    response = test_app.delete(f"/Groups/{group.id}", headers=headers)
    assert response.status_code == 204


def test_update_group(test_app):
    headers = {
      'x-api-key': "secret"
    }

    data = {
      "displayName": "testgroup"
    }

    response = test_app.post("/Groups", json=data, headers=headers)
    assert response.status_code == 201
    group = GroupResource(**response.json())

    response = test_app.get(f"/Groups/{group.id}", headers=headers)
    assert response.status_code == 200
    group = GroupResource(**response.json())
    group.displayName = 'testgroup2'

    data = group.json()
    response = test_app.put(f"/Groups/{group.id}", data=data, headers=headers)
    assert response.status_code == 200


def test_delete_group(test_app):
    headers = {
      'x-api-key': "secret"
    }

    data = {
      "displayName": "testgroup"
    }

    response = test_app.post("/Groups", json=data, headers=headers)
    assert response.status_code == 201
    group = GroupResource(**response.json())
    response = test_app.delete(f"/Groups/{group.id}", headers=headers)
    assert response.status_code == 204
