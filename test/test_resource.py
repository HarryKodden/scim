# import test_resource.py

from schema import resourceTypes

import logging
logger = logging.getLogger(__name__)


def test_get_resources(test_app):
    response = test_app.get("/ResourceTypes")
    assert response.status_code == 200

    for id in [resource.id for resource in resourceTypes]:

        response = test_app.get(f"/ResourceTypes/{id}")
        assert response.status_code == 200


def test_get_invlaid_resources(test_app):
    response = test_app.get("/ResourceTypes/foobar")
    assert response.status_code == 404
