from typing import Any
import uuid
import os


class Plugin(object):
    """Base class that each plugin must inherit from. within this class
    you must define the methods that all of your plugins must implement
    """

    USERS = os.environ.get("USER_model_name", "Users")
    GROUPS = os.environ.get("GROUP_model_name", "Groups")

    def __init__(self):
        self.description = 'UNKNOWN'

    def id(self) -> str:
        return str(uuid.uuid4())

    def __iter__(self) -> Any:
        raise NotImplementedError

    def __delete__(self, id: str) -> None:
        raise NotImplementedError

    def __getitem__(self, id: str) -> Any:
        raise NotImplementedError

    def __setitem__(self, id: str, details: Any) -> None:
        raise NotImplementedError
