
# import test_config.py

from events.mapping import DEFAULT_NOTICE_EVENT_URIS
from scim_errors import SCIM_EVENTS_EXTENSION


def test_apidoc(test_app):
    response = test_app.get("/ServiceProviderConfig")
    assert response.status_code == 200
    body = response.json()
    assert body.get("patch", {}).get("supported") is True
    assert body.get("etag", {}).get("supported") is True
    assert SCIM_EVENTS_EXTENSION in body.get("schemas", [])
    security = body.get(SCIM_EVENTS_EXTENSION)
    assert security is not None
    assert security.get("asyncRequest") == "none"
    for uri in DEFAULT_NOTICE_EVENT_URIS:
        assert uri in security.get("eventUris", [])
    auth_types = {s["type"] for s in body.get("authenticationSchemes", [])}
    assert auth_types <= {
        "oauth",
        "oauth2",
        "oauthbearertoken",
        "httpbasic",
        "httpdigest",
    }
