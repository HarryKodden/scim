import os
import json

from typing import Any
from data.plugins import Plugin

from pathlib import Path

class FilePlugin(Plugin):

    def __init__(self, path: str):
      self.path = path
      self.description = 'FILE STORAGE'

      Path(f"{self.path}/Users").mkdir(parents=True, exist_ok=True)
      Path(f"{self.path}/Groups").mkdir(parents=True, exist_ok=True)

    def iterate(self, resource_type: str) -> Any:
      for id in os.listdir(f"{self.path}/{resource_type}"):
        yield id

    def delete(self, resource_type: str, id: int) -> None:
      os.unlink(f"{self.path}/{resource_type}/{id}")

    def read(self, resource_type: str, id: int) -> Any:
      try:
        with open(f"{self.path}/{resource_type}/{id}", "rb") as f:
          return json.loads(f.read())
      except Exception:
        return None

    def write(self, resource_type: str, id: int, details: Any) -> None:
      with open(f"{self.path}/{resource_type}/{id}", "wb") as f:
        f.write(
          json.dumps(
            json.loads(details),
            indent=2
          ).encode()
        )
