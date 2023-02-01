# data/__init__.py

import os
import uuid
import json

from typing import Any
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

DATA_PATH = os.environ.get("DATA_PATH", "/tmp")

PATH_USERS = f"{DATA_PATH}/Users"
PATH_GROUPS = f"{DATA_PATH}/Groups"


def generate_uuid() -> str:
    return str(uuid.uuid4())


def init_data() -> None:
    logger.debug(f"Initializing data directories at: {DATA_PATH}")

    Path(PATH_USERS).mkdir(parents=True, exist_ok=True)
    Path(PATH_GROUPS).mkdir(parents=True, exist_ok=True)


def read(path: str) -> Any:
    try:
        with open(path, "rb") as f:
            return json.loads(f.read())
    except Exception:
        return None


def write(path: str, details: Any) -> None:
    with open(path, "wb") as f:
        f.write(
            json.dumps(
                json.loads(details),
                indent=2
            ).encode()
        )
