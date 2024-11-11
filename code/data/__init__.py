# data/__init__.py

import os

# Backend option: LDAP
DEFAULT_LDAP_BASENAME = "dc=example,dc=org"

ldap_hostname = os.environ.get("LDAP_HOSTNAME", None)
ldap_username = os.environ.get("LDAP_USERNAME", f"cn=admin,{DEFAULT_LDAP_BASENAME}")
ldap_password = os.environ.get("LDAP_PASSWORD", None)
ldap_basename = os.environ.get("LDAP_BASENAME", DEFAULT_LDAP_BASENAME)

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

# Datamodels for Users & Groups
user_model = os.environ.get("USER_model_name", "Users")
group_model = os.environ.get("GROUP_model_name", "Groups")

if ldap_hostname:
    from data.plugins.ldap import LDAP_Plugin

    def user_dn(cls):
        return f"ou={user_model},{ldap_basename}"
    def group_dn(cls):
        return f"ou={group_model},{ldap_basename}"
    
    LDAP_Plugin.user_dn = classmethod(user_dn)
    LDAP_Plugin.group_dn = classmethod(group_dn)
    
    Users = LDAP_Plugin(user_model, ldap_hostname, ldap_username, ldap_password)
    Groups = LDAP_Plugin(group_model, ldap_hostname, ldap_username, ldap_password)

elif mongo_db:
    from data.plugins.mongo import MongoPlugin

    Users = MongoPlugin(user_model, mongo_db)
    Groups = MongoPlugin(group_model, mongo_db)
elif database_url:
    from data.plugins.sql import SQLPlugin

    Users = SQLPlugin(user_model, database_url)
    Groups = SQLPlugin(group_model, database_url)
elif jumpcloud_url:
    from data.plugins.jumpcloud import JumpCloudPlugin

    Users = JumpCloudPlugin(
        user_model,
        jumpcloud_url,
        jumpcloud_key
    )
    Groups = JumpCloudPlugin(
        group_model,
        jumpcloud_url,
        jumpcloud_key
    )
elif scim_forward_url:
    from data.plugins.scim import SCIM_Forward_Plugin

    Users = SCIM_Forward_Plugin(
        user_model,
        scim_forward_url,
        scim_forward_key
    )
    Groups = SCIM_Forward_Plugin(
        group_model,
        scim_forward_url,
        scim_forward_key
    )
else:
    from data.plugins.file import FilePlugin

    Users = FilePlugin(user_model, data_path)
    Groups = FilePlugin(group_model, data_path)
