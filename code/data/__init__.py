import uuid
import json

from typing import Any
from pathlib import Path

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PATH_USERS = "/data/Users"
PATH_GROUPS = "/data/Groups"


def generate_uuid():
  return str(uuid.uuid4())


def init_data():
  Path(PATH_USERS).mkdir(parents=True, exist_ok=True)
  Path(PATH_GROUPS).mkdir(parents=True, exist_ok=True)


def read(path: str) -> Any:
  try:
    with open(path, "rb") as f:
      return json.loads(f.read())
  except:
    return None


def write(path: str, details: Any) -> None:
  with open(path, "wb") as f:
    f.write(
      json.dumps(
        json.loads(details),
        indent=2
      ).encode()
    )
