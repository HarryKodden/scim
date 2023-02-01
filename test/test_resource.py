# import test_resource.py

from schema import resourceTypes

import logging
logger = logging.getLogger(__name__)


def test_get_resources(test_app):
    headers = {
      'x-api-key': "secret"
    }

    response = test_app.get("/ResourceTypes", headers=headers)
    assert response.status_code == 200

    for id in [resource.id for resource in resourceTypes]:

        response = test_app.get(f"/ResourceTypes/{id}", headers=headers)
        assert response.status_code == 200
