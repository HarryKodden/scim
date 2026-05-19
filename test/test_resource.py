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
    body = response.json()
    assert body["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:Error"]
    assert body["status"] == "404"
    assert "foobar" in body["detail"]
    assert response.headers.get("content-type", "").startswith(
        "application/scim+json"
    )


def test_resource_types_omit_null_meta_etag(test_app):
    response = test_app.get("/ResourceTypes")
    for item in response.json()["Resources"]:
        meta = item.get("meta", {})
        assert "etag" not in meta or meta["etag"] is not None
