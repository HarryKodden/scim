# data/__init__.py

import os
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

from data.plugins.file import FilePlugin
from data.plugins.mongo import MongoPlugin
from data.plugins.mysql import MySQLPlugin

plugin = FilePlugin(os.environ.get("DATA_PATH", "/tmp"))