# import test_validation.py

import logging
logger = logging.getLogger(__name__)


def test_user_validation(test_app):
    headers = {
        'x-api-key': "secret",
        'content-type': 'application/scim+json'
    }

    response = test_app.post(
        "/Users",
        json={
            "foo": "bar",
            "active": True
        },
        headers=headers
    )
    assert response.status_code == 422


def test_group_validation(test_app):
    headers = {
        'x-api-key': "secret",
        'content-type': 'application/scim+json'
    }

    response = test_app.post(
        "/Groups",
        json={
            "foo": "bar",
        },
        headers=headers
    )
    assert response.status_code == 422
