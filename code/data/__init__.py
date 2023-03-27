# data/__init__.py

import os
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

from data.plugins.file import FilePlugin
from data.plugins.mongo import MongoPlugin
from data.plugins.sql import SQLPlugin

#Users = SQLPlugin('Users')
#Groups = SQLPlugin('Groups')

Users = SQLPlugin('Users', database_url=os.environ.get("MYSQL_URL"))
Groups = SQLPlugin('Groups', database_url=os.environ.get("MYSQL_URL"))

#Users = MongoPlugin("Users")
#Groups = MongoPlugin("Groups")

#Users = FilePlugin("Users")
#Groups = FilePlugin("Groups")