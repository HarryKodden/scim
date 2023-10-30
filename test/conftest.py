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


@pytest.fixture(scope="module")
def test_app(setup_data):
    from main import app

    client = TestClient(app)
    yield client
