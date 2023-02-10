# data/__init__.py

import os
import uuid
import json

from typing import Any
from pathlib import Path

import pymongo

import logging
logger = logging.getLogger(__name__)

DATA_PATH = os.environ.get("DATA_PATH", "/tmp")


def generate_uuid() -> str:
    return str(uuid.uuid4())


def init_data() -> None:
    logger.debug(f"Initializing data directories at: {DATA_PATH}")

    if DATA_PATH.startswith('mongodb://'):
        pass
    else:
        Path(f"{DATA_PATH}/Users").mkdir(parents=True, exist_ok=True)
        Path(f"{DATA_PATH}/Groups").mkdir(parents=True, exist_ok=True)


def iterate(resource_type: str) -> Any:
    if DATA_PATH.startswith('mongodb://'):
        for record in pymongo.MongoClient(
            DATA_PATH
        )["scim"][resource_type].find({}):
            yield record.pop("_id")
    else:
        for id in os.listdir(f"{DATA_PATH}/{resource_type}"):
            yield id


def delete(resource_type: str, id: int) -> None:
    if DATA_PATH.startswith('mongodb://'):
        pymongo.MongoClient(
            DATA_PATH
        )["scim"][resource_type].delete_one({"_id": id})
    else:
        os.unlink(f"{DATA_PATH}/{resource_type}/{id}")


def read(resource_type: str, id: int) -> Any:
    if DATA_PATH.startswith('mongodb://'):
        record = pymongo.MongoClient(
            DATA_PATH
        )["scim"][resource_type].find_one({"_id": id})
        if record:
            record["id"] = record.pop("_id")
        return record
    else:
        try:
            with open(f"{DATA_PATH}/{resource_type}/{id}", "rb") as f:
                return json.loads(f.read())
        except Exception:
            return None


def write(resource_type: str, id: int, details: Any) -> None:
    if DATA_PATH.startswith('mongodb://'):
        if read(resource_type, id):
            logger.debug("UPDATE")
            pymongo.MongoClient(DATA_PATH)["scim"][resource_type].update_one(
                {"_id": id},
                {"$set": json.loads(details)}
            )

        else:
            logger.debug("INSERT")
            pymongo.MongoClient(DATA_PATH)["scim"][resource_type].insert_one(
                {"_id": id} | json.loads(details)
            )
    else:
        with open(f"{DATA_PATH}/{resource_type}/{id}", "wb") as f:
            f.write(
                json.dumps(
                    json.loads(details),
                    indent=2
                ).encode()
            )
