# data/__init__.py

import os

user_model_name = os.environ.get("USER_MODEL_NAME", "Users")
group_model_name = os.environ.get("GROUP_MODEL_NAME", "Groups")

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

if mongo_db:
    from data.plugins.mongo import MongoPlugin
    Users = MongoPlugin(user_model_name, mongo_db)
    Groups = MongoPlugin(group_model_name, mongo_db)

elif database_url:
    from data.plugins.sql import SQLPlugin

    Users = SQLPlugin(user_model_name, database_url)
    Groups = SQLPlugin(group_model_name, database_url)
elif jumpcloud_url:
    from data.plugins.jumpcloud import JumpCloudPlugin

    Users = JumpCloudPlugin(user_model_name, jumpcloud_url, jumpcloud_key)
    Groups = JumpCloudPlugin(group_model_name, jumpcloud_url, jumpcloud_key)
elif scim_forward_url:
    from data.plugins.scim import SCIM_Forward_Plugin

    Users = SCIM_Forward_Plugin(user_model_name, scim_forward_url, scim_forward_key)
    Groups = SCIM_Forward_Plugin(group_model_name, scim_forward_url, scim_forward_key)
else:
    from data.plugins.file import FilePlugin

    Users = FilePlugin(user_model_name, data_path)
    Groups = FilePlugin(group_model_name, data_path)
