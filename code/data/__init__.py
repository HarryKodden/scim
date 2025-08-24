# data/__init__.py

import os

from data.plugins import Plugin

# Backend option: LDAP
DEFAULT_LDAP_BASENAME = "dc=example,dc=org"

ldap_hostname = os.environ.get("LDAP_HOSTNAME", None)
ldap_basename = os.environ.get(
    "LDAP_BASENAME", DEFAULT_LDAP_BASENAME
)
ldap_username = os.environ.get(
    "LDAP_USERNAME", f"cn=admin,{DEFAULT_LDAP_BASENAME}"
)
ldap_password = os.environ.get("LDAP_PASSWORD", None)

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

# Backend option: iRODS
irods_host = os.environ.get("IRODS_HOST", None)
irods_port = int(os.environ.get("IRODS_PORT", "1247"))
irods_zone = os.environ.get("IRODS_ZONE", None)
irods_admin_username = os.environ.get("IRODS_ADMIN_USERNAME", None)
irods_admin_password = os.environ.get("IRODS_ADMIN_PASSWORD", None)

user_model = Plugin().USERS
group_model = Plugin().GROUPS


if ldap_hostname:
    from data.plugins.ldap import LDAP_Plugin

    def user_dn(cls):
        return f"ou={user_model},{ldap_basename}"

    def group_dn(cls):
        return f"ou={group_model},{ldap_basename}"

    LDAP_Plugin.user_dn = classmethod(user_dn)
    LDAP_Plugin.group_dn = classmethod(group_dn)

    Users = LDAP_Plugin(
        user_model, ldap_hostname, ldap_username, ldap_password
    )
    Groups = LDAP_Plugin(
        group_model, ldap_hostname, ldap_username, ldap_password
    )

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
elif irods_host:
    from data.plugins.irods import iRODSPlugin

    Users = iRODSPlugin(
        user_model,
        irods_host,
        irods_port,
        irods_admin_username,
        irods_admin_password,
        irods_zone
    )
    Groups = iRODSPlugin(
        group_model,
        irods_host,
        irods_port,
        irods_admin_username,
        irods_admin_password,
        irods_zone
    )
else:
    from data.plugins.file import FilePlugin

    Users = FilePlugin(user_model, data_path)
    Groups = FilePlugin(group_model, data_path)
