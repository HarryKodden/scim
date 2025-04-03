# conftest.py

import os
import pytest
import tempfile
import shutil

from fastapi.testclient import TestClient

import logging
logging.getLogger('asyncio').setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def setup_data(request):
    def finalizer():
        logging.debug(f"[DATA] Remove: {os.environ['DATA_PATH']}")
        shutil.rmtree(os.environ['DATA_PATH'])

    os.environ['DATA_PATH'] = tempfile.mkdtemp()
    logging.debug(f"[DATA] Create: {os.environ['DATA_PATH']}")

    request.addfinalizer(finalizer)

    return request


@pytest.fixture(scope="session")
def register_schemas():
    """Register all dynamic schemas once before any tests run."""
    from schema import register_schemas, Group, User
    logging.info("[SCHEMA] Registering dynamic schemas")
    register_schemas()

    # Add verification that schemas are loaded
    logging.info(f"Group schema attributes: {vars(Group)}")
    logging.info(f"User schema attributes: {vars(User)}")

    # Check if expected attributes are present
    assert hasattr(Group, "members"), \
        "Group schema is missing members attribute!"
    assert hasattr(Group, "displayName"), \
        "Group schema is missing displayName attribute!"
    assert hasattr(Group, "externalId"), \
        "Group schema is missing externalId attribute!"
    assert hasattr(User, "userName"), \
        "User schema is missing userName attribute!"
    assert hasattr(User, "name"), \
        "User schema is missing name attribute!"

    yield


@pytest.fixture(scope="module")
def test_app(setup_data):
    from main import app

    client = TestClient(app)
    yield client
