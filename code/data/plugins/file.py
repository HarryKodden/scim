import os
import json

from typing import Any
from data.plugins import Plugin

from pathlib import Path

class FilePlugin(Plugin):

    def __init__(self, resource_type: str, path: str):
      self.path = path
      self.resource_type = resource_type
      self.description = 'FILE STORAGE'

      Path(f"{self.path}/Users").mkdir(parents=True, exist_ok=True)
      Path(f"{self.path}/Groups").mkdir(parents=True, exist_ok=True)

    def __iter__(self) -> Any:
      for id in os.listdir(f"{self.path}/{self.resource_type}"):
        yield id

    def __delete__(self, id: str) -> None:
      os.unlink(f"{self.path}/{self.resource_type}/{id}")

    def __getitem__(self, id: str) -> Any:
      try:
        with open(f"{self.path}/{self.resource_type}/{id}", "rb") as f:
          return json.loads(f.read())
      except Exception:
        return None

    def __setitem__(self, id: str, details: Any) -> None:
      with open(f"{self.path}/{self.resource_type}/{id}", "wb") as f:
        f.write(
          json.dumps(
            json.loads(details),
            indent=2
          ).encode()
        )
