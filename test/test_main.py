
import pytest

from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def test_app():
    from main import app
    client = TestClient(app)
    yield client  # testing happens here


def test_apidoc(test_app):
    response = test_app.get("/apidoc")
    assert response.status_code == 200


def test_get_users(test_app):
    headers = {
      'API-KEY': "secret"
    }

    response = test_app.get("/Users", headers=headers)
    assert response.status_code == 200

def test_delete_users(test_app):
    headers = {
      'API-KEY': "secret"
    }

    response = test_app.delete("/Users/xxxx", headers=headers)
    assert response.status_code == 204
