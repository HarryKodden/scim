# filter.py

from typing import Any


def process_filter(filter: str, resource: Any) -> bool:
  """ Process filter to see if resource matches filter conditions
  """

  if not filter:
    return True
  