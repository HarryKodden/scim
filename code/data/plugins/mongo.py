import json

from pymongo import MongoClient
from typing import Any
from data.plugins import Plugin

class MongoPlugin(Plugin):

    def __init__(self, connection: str):
      self.connection = connection
      self.description = 'MONGO'

    def iterate(self, resource_type: str) -> Any:
      for record in MongoClient(
        self.connection
      )["scim"][resource_type].find({}):
        yield record.pop("_id")

    def delete(self, resource_type: str, id: int) -> None:
      MongoClient(
        self.connection
      )["scim"][resource_type].delete_one({"_id": id})

    def read(self, resource_type: str, id: int) -> Any:
      record = MongoClient(
        self.connection
      )["scim"][resource_type].find_one({"_id": id})
      if record:
        record["id"] = record.pop("_id")
      return record

    def write(self, resource_type: str, id: int, details: Any) -> None:
      if self.read(resource_type, id):
        MongoClient(
          self.connection
        )["scim"][resource_type].update_one(
          {"_id": id},
          {"$set": json.loads(details)}
        )
      else:
        pymongo.MongoClient(
          self.connection
        )["scim"][resource_type].insert_one(
          {"_id": id} | json.loads(details)
        )







