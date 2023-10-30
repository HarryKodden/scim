import os
import json

from typing import Any
from data.plugins import Plugin

from pathlib import Path

import logging
logger = logging.getLogger(__name__)


class FilePlugin(Plugin):

    def __init__(
        self,
        resource_type: str,
        data_path: str = "/tmp"
    ):
        self.data_path = data_path
        self.resource_type = resource_type
        self.description = 'FILE STORAGE'

        Path(f"{self.data_path}/Users").mkdir(parents=True, exist_ok=True)
        Path(f"{self.data_path}/Groups").mkdir(parents=True, exist_ok=True)

    def __iter__(self) -> Any:
        logger.debug(f"[__iter__]: {self.description}")

        for id in os.listdir(f"{self.data_path}/{self.resource_type}"):
            yield id

    def __delitem__(self, id: str) -> None:
        logger.debug(f"[__delitem__]: {self.description}, id={id}")

        os.unlink(f"{self.data_path}/{self.resource_type}/{id}")

    def __getitem__(self, id: str) -> Any:
        logger.debug(f"[__getitem__]: {self.description}, id={id}")

        try:
            with open(
                f"{self.data_path}/{self.resource_type}/{id}",
                "rb"
            ) as f:
                return json.loads(f.read())
        except Exception:
            return None

    def __setitem__(self, id: str, details: Any) -> None:
        logger.debug(
            f"[__setitem__]: {self.description}, id:{id}, details: {details}"
        )

        with open(
            f"{self.data_path}/{self.resource_type}/{id}",
            "wb"
        ) as f:
            f.write(
                json.dumps(
                    json.loads(details),
                    indent=2
                ).encode()
            )
