from typing import Any

class Plugin(object):
    """Base class that each plugin must inherit from. within this class
    you must define the methods that all of your plugins must implement
    """

    def __init__(self):
        self.description = 'UNKNOWN'

    def iterate(self, resource_type: str) -> Any:
        raise NotImplementedError

    def delete(self, resource_type: str, id: int) -> None:
        raise NotImplementedError

    def read(self, resource_type: str, id: int) -> Any:
        raise NotImplementedError

    def write(self, resource_type: str, id: int, details: Any) -> None:
        raise NotImplementedError

