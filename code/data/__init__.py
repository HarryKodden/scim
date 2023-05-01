# data/__init__.py

import os
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


# Backend option: Mongo DB
mongo_db = os.environ.get("MONGO_DB", None)

# Backend option: SQL Databases
database_url = os.environ.get("DATABASE_URL", None)

# Backend option: File
data_path = os.environ.get("DATA_PATH", "/tmp")

# Backend option: Jumpcloud
jumpcloud_url = os.environ.get("JUMPCLOUD_URL", None)
jumpcloud_key = os.environ.get("JUMPCLOUD_KEY", None)


if mongo_db:
    from data.plugins.mongo import MongoPlugin

    Users = MongoPlugin("Users", mongo_db)
    Groups = MongoPlugin("Groups", mongo_db)
elif database_url:
    from data.plugins.sql import SQLPlugin

    Users = SQLPlugin('Users', database_url)
    Groups = SQLPlugin('Groups', database_url)
elif jumpcloud_url:
    from data.plugins.jumpcloud import JumpCloudPlugin

    Users = JumpCloudPlugin('Users', jumpcloud_url, jumpcloud_key)
    Groups = JumpCloudPlugin('Groups', jumpcloud_url, jumpcloud_key)
else:
    from data.plugins.file import FilePlugin

    Users = FilePlugin('Users', data_path)
    Groups = FilePlugin('Groups', data_path)
