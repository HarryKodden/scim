# data/__init__.py

import os

# Backend option: Mongo DB
mongo_db = os.environ.get("MONGO_DB", None)

# Backend option: SQL Databases
database_url = os.environ.get("DATABASE_URL", None)

# Backend option: File
data_path = os.environ.get("DATA_PATH", "/tmp")

# Backend option: Jumpcloud
jumpcloud_url = os.environ.get("JUMPCLOUD_URL", None)
jumpcloud_key = os.environ.get("JUMPCLOUD_KEY", None)

# Backend option: SCIM Forward
scim_forward_url = os.environ.get("SCIM_FORWARD_URL", None)
scim_forward_key = os.environ.get(
    "SCIM_FORWARD_KEY",
    os.environ.get("API_KEY", "secret")
)

# Backend option: NetBird
netbird_url = os.environ.get("NETBIRD_URL", None)
netbird_token = os.environ.get("NETBIRD_TOKEN", None)


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
elif scim_forward_url:
    from data.plugins.scim import SCIM_Forward_Plugin

    Users = SCIM_Forward_Plugin('Users', scim_forward_url, scim_forward_key)
    Groups = SCIM_Forward_Plugin('Groups', scim_forward_url, scim_forward_key)
elif netbird_url:
    from data.plugins.netbird import NetBird

    Users = NetBird('Users', netbird_url, netbird_token)
    Groups = NetBird('Groups', netbird_url, netbird_token)
else:
    from data.plugins.file import FilePlugin

    Users = FilePlugin('Users', data_path)
    Groups = FilePlugin('Groups', data_path)
