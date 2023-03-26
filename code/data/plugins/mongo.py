import json

from pymongo import MongoClient
from typing import Any
from data.plugins import Plugin

class MongoPlugin(Plugin):

    def __init__(self, resource_type: str, address: str):
      self.connection = MongoClient(address)["scim"][resource_type]
      self.description = f"MONGO-{resource_type}"

    def __iter__(self) -> Any:
      for record in self.connection.find({}):
        yield record.pop("_id")

    def __del__(self, id: str) -> None:
      self.connection.delete_one({"_id": id})

    def __getitem__(self, id: str) -> Any:
      record = self.connection.find_one({"_id": id})
      if record:
        record["id"] = record.pop("_id")
      return record

    def __setitem(self, id: str, details: Any) -> None:
      if self[id]:
        self.connection.update_one(
          {"_id": id},
          {"$set": json.loads(details)}
        )
      else:
        self.connection.insert_one(
          {"_id": id} | json.loads(details)
        )







