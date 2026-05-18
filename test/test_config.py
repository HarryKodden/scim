
# import test_docs.py

from events.mapping import DEFAULT_NOTICE_EVENT_URIS


def test_apidoc(test_app):
    response = test_app.get("/ServiceProviderConfig")
    assert response.status_code == 200
    body = response.json()
    assert body.get("patch", {}).get("supported") is True
    security = body.get("securityEvents")
    assert security is not None
    assert security.get("asyncRequest") == "none"
    for uri in DEFAULT_NOTICE_EVENT_URIS:
        assert uri in security.get("eventUris", [])
