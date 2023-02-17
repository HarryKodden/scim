# conftest.py

import pytest

from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def setup_data():
    from main import startup
    startup()


@pytest.fixture(scope="module")
def test_app(setup_data):
    from main import app, BASE_PATH

    client = TestClient(app)
    client.base_url += BASE_PATH
    yield client
