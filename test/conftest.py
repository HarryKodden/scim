# conftest.py

import pytest

from fastapi.testclient import TestClient

import logging
logging.getLogger('asyncio').setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def setup_data():
    pass


@pytest.fixture(scope="module")
def test_app(setup_data):
    from main import app

    client = TestClient(app)
    yield client
