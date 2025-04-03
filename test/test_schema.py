# import test_schema.py


from schema import Schemas

import logging
logger = logging.getLogger(__name__)


def test_get_schemas(test_app):
    response = test_app.get("/Schemas")
    assert response.status_code == 200

    schemas = {**Schemas['User'], **Schemas['Group']}
    
    for id in schemas.keys():
        response = test_app.get(f"/Schemas/{id}")
        assert response.status_code == 200


def test_get_invalid_schemas(test_app):
    response = test_app.get("Schemas/foobar")
    assert response.status_code == 404
