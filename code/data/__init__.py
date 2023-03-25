# data/__init__.py

import os
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

from data.plugins.file import FilePlugin
from data.plugins.mongo import MongoPlugin
from data.plugins.mysql import MySQLPlugin

#plugin = FilePlugin(os.environ.get("DATA_PATH", "/tmp"))
#plugin = MongoPlugin("mongodb://mongo:secret@mongo")
Users = MySQLPlugin("Users", "mysql", "root", "secret", "mysql")
Groups = MySQLPlugin("Groups", "mysql", "root", "secret", "mysql")