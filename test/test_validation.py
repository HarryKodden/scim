# import test_validation.py

import logging
logger = logging.getLogger(__name__)


def test_user_validation(test_app):
    headers = {
        'x-api-key': "secret",
        'content-type': 'application/scim+json'
    }

    data = {
        "foo": "bar",
        "active": True
    }

    response = test_app.post("/Users", json=data, headers=headers)
    assert response.status_code == 422


def test_group_validation(test_app):
    headers = {
        'x-api-key': "secret",
        'content-type': 'application/scim+json'
    }

    data = {
        "foo": "bar",
    }

    response = test_app.post("/Groups", json=data, headers=headers)
    assert response.status_code == 422
