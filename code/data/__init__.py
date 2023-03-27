# data/__init__.py

import os
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


mongo_db = os.environ.get("MONGO_DB", None)
database_url = os.environ.get("DATABASE_URL", None)
data_path = os.environ.get("DATA_PATH", "/tmp")

if mongo_db:
    from data.plugins.mongo import MongoPlugin

    Users = MongoPlugin("Users", mongo_db)
    Groups = MongoPlugin("Groups", mongo_db)
elif database_url:
    from data.plugins.sql import SQLPlugin

    Users = SQLPlugin('Users', database_url)
    Groups = SQLPlugin('Groups', database_url)
else:
    from data.plugins.file import FilePlugin

    Users = FilePlugin('Users', data_path)
    Groups = FilePlugin('Groups', data_path)
