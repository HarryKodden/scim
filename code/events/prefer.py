# events/prefer.py

"""RFC 7240 Prefer header parsing for async SCIM (RFC 9967 §2.5.1.1)."""

import re
from typing import Optional


def wants_respond_async(prefer_header: Optional[str]) -> bool:
    if not prefer_header:
        return False
    parts = [p.strip().lower() for p in prefer_header.split(",")]
    return "respond-async" in parts


def parse_wait_seconds(prefer_header: Optional[str]) -> Optional[float]:
    """
    Parse wait=N from Prefer header (RFC 7240 §4.3).
    Returns seconds or None if not present.
    """
    if not prefer_header:
        return None
    match = re.search(r"wait\s*=\s*(\d+(?:\.\d+)?)", prefer_header, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None
