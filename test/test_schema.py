# import test_schema.py


from schema import Schemas

import logging
logger = logging.getLogger(__name__)


def test_get_schemas(test_app):
    headers = {
      'x-api-key': "secret"
    }

    response = test_app.get("/Schemas", headers=headers)
    assert response.status_code == 200

    for id in Schemas.keys():
        response = test_app.get(f"/Schemas/{id}", headers=headers)
        assert response.status_code == 200
