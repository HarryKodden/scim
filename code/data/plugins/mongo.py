import os
import json

from pymongo import MongoClient
from typing import Any
from data.plugins import Plugin

import logging
logger = logging.getLogger(__name__)


class MongoPlugin(Plugin):

    def __init__(
      self,
      resource_type: str, mongo_db: str = os.environ.get("MONGO_DB", "mongodb://localhost:27017/")
    ):
      self.connection = MongoClient(mongo_db)["scim"][resource_type]
      self.description = f"MONGO-{resource_type}"

    def __iter__(self) -> Any:
      logger.debug(f"[__iter__]: {self.description}")

      for record in self.connection.find({}):
        yield record.pop("_id")

    def __delitem__(self, id: str) -> None:
      logger.debug(f"[__delitem__]: {self.description}, id={id}")

      self.connection.delete_one({"_id": id})

    def __getitem__(self, id: str) -> Any:
      logger.debug(f"[__getitem__]: {self.description}, id={id}")

      record = self.connection.find_one({"_id": id})
      if record:
        record["id"] = record.pop("_id")
      return record

    def __setitem__(self, id: str, details: Any) -> None:
      logger.debug(f"[__setitem__]: {self.description}, id:{id}, details: {details}")

      if self[id]:
        self.connection.update_one(
          {"_id": id},
          {"$set": json.loads(details)}
        )
      else:
        self.connection.insert_one(
          {"_id": id} | json.loads(details)
        )







