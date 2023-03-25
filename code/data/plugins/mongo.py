import json

from pymongo import MongoClient
from typing import Any
from data.plugins import Plugin

class MongoPlugin(Plugin):

    def __init__(self, resource_type: str, connection: str):
      self.resource_type = resource_type
      self.connection = connection
      self.description = f"MYSQL-{resource_type}"

    def __iter__(self) -> Any:
      for record in MongoClient(
        self.connection
      )["scim"][self.resource_type].find({}):
        yield record.pop("_id")

    def __del__(self, id: str) -> None:
      MongoClient(
        self.connection
      )["scim"][self.resource_type].delete_one({"_id": id})

    def __getitem__(self, id: str) -> Any:
      record = MongoClient(
        self.connection
      )["scim"][self.resource_type].find_one({"_id": id})
      if record:
        record["id"] = record.pop("_id")
      return record

    def __setitem(self, id: str, details: Any) -> None:
      if self[id]:
        MongoClient(
          self.connection
        )["scim"][self.resource_type].update_one(
          {"_id": id},
          {"$set": json.loads(details)}
        )
      else:
        MongoClient(
          self.connection
        )["scim"][self.resource_type].insert_one(
          {"_id": id} | json.loads(details)
        )







