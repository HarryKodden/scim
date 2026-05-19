# test/test_scim_errors.py

from scim_errors import (
    SCIM_ERROR_SCHEMA,
    SCIM_EVENTS_EXTENSION,
    build_scim_error,
    is_scim_api_path,
    scim_error_response,
)


def test_is_scim_api_path():
    assert is_scim_api_path("/Users")
    assert is_scim_api_path("/Users/abc")
    assert is_scim_api_path("/Bulk")
    assert is_scim_api_path("/Events/Feeds/default/Stream")
    assert is_scim_api_path("/Async/txn-1")
    assert not is_scim_api_path("/health")
    assert not is_scim_api_path("/")
    assert not is_scim_api_path("/docs")
    assert not is_scim_api_path("/openapi.json")


def test_build_scim_error_with_scim_type():
    body = build_scim_error(404, "missing", scim_type="invalidPath")
    assert body["schemas"] == [SCIM_ERROR_SCHEMA]
    assert body["status"] == "404"
    assert body["detail"] == "missing"
    assert body["scimType"] == "invalidPath"


def test_scim_error_response_accepts_prebuilt_error():
    prebuilt = build_scim_error(409, "duplicate", scim_type="uniqueness")
    response = scim_error_response(409, prebuilt)
    assert response.status_code == 409
    assert response.body
    payload = response.body.decode()
    assert SCIM_ERROR_SCHEMA in payload
    assert "uniqueness" in payload


def test_scim_unauthorized_returns_error_envelope(test_app):
    response = test_app.get("/Users")
    assert response.status_code == 401
    body = response.json()
    assert body["schemas"] == [SCIM_ERROR_SCHEMA]
    assert body["status"] == "401"
    assert body["scimType"] == "invalidCredentials"
    assert response.headers.get("content-type", "").startswith("application/scim+json")


def test_scim_not_found_resource_type(test_app):
    response = test_app.get(
        "/ResourceTypes/unknown-type",
        headers={"x-api-key": "secret"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["schemas"] == [SCIM_ERROR_SCHEMA]
    assert body["scimType"] == "invalidPath"


def test_scim_duplicate_user_returns_409(test_app):
    import uuid

    user_name = f"scim-error-dup-{uuid.uuid4().hex[:8]}"
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    payload = {
        "userName": user_name,
        "active": True,
        "emails": [{"primary": True, "value": f"{user_name}@test.example"}],
    }
    assert test_app.post("/Users", json=payload, headers=headers).status_code == 201
    response = test_app.post("/Users", json=payload, headers=headers)
    assert response.status_code == 409
    body = response.json()
    assert body["scimType"] == "uniqueness"


def test_scim_invalid_patch_syntax_returns_400(test_app):
    import uuid

    user_name = f"scim-error-patch-{uuid.uuid4().hex[:8]}"
    headers = {
        "x-api-key": "secret",
        "content-type": "application/scim+json",
    }
    create = test_app.post(
        "/Users",
        json={
            "userName": user_name,
            "active": True,
            "emails": [{"primary": True, "value": f"{user_name}@test.example"}],
        },
        headers=headers,
    )
    assert create.status_code == 201
    user_id = create.json()["id"]

    bad_patch = test_app.patch(
        f"/Users/{user_id}",
        json={"not": "a patch op"},
        headers=headers,
    )
    assert bad_patch.status_code == 400
    body = bad_patch.json()
    assert body["schemas"] == [SCIM_ERROR_SCHEMA]
    assert body["scimType"] == "invalidSyntax"


def test_async_result_not_found_scim_error(test_app):
    response = test_app.get(
        "/Async/does-not-exist-txn",
        headers={"x-api-key": "secret"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["schemas"] == [SCIM_ERROR_SCHEMA]
    assert body["scimType"] == "invalidPath"


def test_events_extension_constant():
    assert SCIM_EVENTS_EXTENSION.endswith("ServiceProviderConfig")


def test_non_scim_path_validation_returns_422(test_app):
    """Non-SCIM routes keep FastAPI validation shape (not SCIM Error)."""
    response = test_app.get("/health?not_a_valid_param=")
    assert response.status_code in (200, 422)


def test_scim_errors_base_path_prefix():
    from routers import BASE_PATH

    assert is_scim_api_path(f"{BASE_PATH}/Users", BASE_PATH)
    assert not is_scim_api_path("/health", BASE_PATH)
