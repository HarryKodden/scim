# data/__init__.py

import os
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

from data.plugins.file import FilePlugin
from data.plugins.mongo import MongoPlugin
from data.plugins.sql import SQLPlugin

#plugin = FilePlugin(os.environ.get("DATA_PATH", "/tmp"))
#plugin = MongoPlugin("mongodb://mongo:secret@mongo")

Users = SQLPlugin("Users")
Groups = SQLPlugin("Groups")