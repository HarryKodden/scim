# data/__init__.py

import os
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

from data.plugins.mongo import MongoPlugin
from data.plugins.sql import SQLPlugin
from data.plugins.file import FilePlugin

mongo_db = os.environ.get("MONGO_DB", None)
database_url = os.environ.get("MONGO_DB", None)
data_path = os.environ.get("DATA_PATH", "/tmp")

if mongo_db:
    Users = MongoPlugin("Users", mongo_db)
    Groups = MongoPlugin("Groups", mongo_db)
elif database_url:
    Users = SQLPlugin('Users', database_url)
    Groups = SQLPlugin('Groups', database_url)
else:
    Users = FilePlugin('Users', data_path)
    Groups = FilePlugin('Groups', data_path)

