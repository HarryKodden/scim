import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from data.plugins import Plugin

logger = logging.getLogger(__name__)

# MidPoint free-text field used like LDAP "info" / JumpCloud "details":
# stores the SCIM document produced by data/users.py and data/groups.py
# after mapped native attributes have been popped.
SCIM_DETAILS_PATH = "description"


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _poly_name(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("orig") or value.get("norm") or value.get("_value")
    return str(value)


def _parse_scim_details(raw: Any) -> Optional[dict]:
    """Return stored SCIM document, or None if this MidPoint object is not SCIM-managed."""
    if not raw:
        return None
    text = _poly_name(raw) if not isinstance(raw, str) else raw
    if not text:
        return None
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    # Generic SCIM resources always carry schemas; reject unrelated description text.
    if "schemas" not in data:
        return None
    return data


class MidPointClient:
    """Thin MidPoint REST helper — no SCIM awareness."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        host_header: Optional[str] = None,
        timeout: float = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth = HTTPBasicAuth(username, password)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        if host_header:
            self.session.headers["Host"] = host_header

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        response = self.session.request(
            method, url, auth=self.auth, timeout=self.timeout, **kwargs
        )
        if response.status_code >= 400:
            raise Exception(
                f"MidPoint {method} {path} failed with HTTP {response.status_code}: "
                f"{response.text}"
            )
        return response

    def search(self, endpoint: str, filter_text: Optional[str] = None) -> List[dict]:
        payload: Dict[str, Any] = {"query": {}}
        if filter_text:
            payload["query"] = {"filter": {"text": filter_text}}
        response = self.request("POST", f"/{endpoint}/search", json=payload)
        objects = response.json().get("object", {}).get("object", [])
        return _as_list(objects)

    def get(self, endpoint: str, oid: str) -> Optional[dict]:
        try:
            response = self.request("GET", f"/{endpoint}/{oid}")
        except Exception as exc:
            if "HTTP 404" in str(exc):
                return None
            raise
        body = response.json()
        for key in ("user", "role", "object"):
            if key in body:
                return body[key]
        return body

    def create(self, endpoint: str, wrapper_key: str, payload: dict) -> str:
        response = self.request("POST", f"/{endpoint}", json={wrapper_key: payload})
        location = response.headers.get("Location", "")
        oid = location.rstrip("/").split("/")[-1]
        if not oid:
            raise Exception(
                f"MidPoint create {endpoint} succeeded without Location header"
            )
        return oid

    def delete(self, endpoint: str, oid: str) -> None:
        try:
            self.request("DELETE", f"/{endpoint}/{oid}")
        except Exception as exc:
            if "HTTP 404" not in str(exc):
                raise

    def patch(self, endpoint: str, oid: str, item_deltas: List[dict]) -> None:
        self.request(
            "PATCH",
            f"/{endpoint}/{oid}",
            json={"objectModification": {"itemDelta": item_deltas}},
        )

    def list_role_members(self, role_oid: str) -> List[dict]:
        return self.search(
            "users", f'roleMembershipRef matches (oid = "{role_oid}")'
        )

    def assign_role(self, user_oid: str, role_oid: str) -> None:
        self.patch(
            "users",
            user_oid,
            [
                {
                    "modificationType": "add",
                    "path": "assignment",
                    "value": {"targetRef": {"oid": role_oid, "type": "RoleType"}},
                }
            ],
        )

    def unassign_role(self, user_oid: str, role_oid: str) -> None:
        self.patch(
            "users",
            user_oid,
            [
                {
                    "modificationType": "delete",
                    "path": "assignment",
                    "value": {"targetRef": {"oid": role_oid, "type": "RoleType"}},
                }
            ],
        )


def _client_from_env() -> MidPointClient:
    base_url = os.environ.get(
        "MIDPOINT_URL", "http://midpoint:8080/midpoint/ws/rest"
    )
    username = os.environ.get("MIDPOINT_USERNAME", "administrator")
    password = os.environ.get("MIDPOINT_PASSWORD", "")
    host_header = os.environ.get("MIDPOINT_HOST_HEADER") or None
    if not password:
        raise Exception("MIDPOINT_PASSWORD is required for the MidPoint SCIM plugin")
    return MidPointClient(base_url, username, password, host_header=host_header)


class MidPointPlugin(Plugin):
    """MidPoint storage backend for SCIM Users/Groups.

    Same contract as File/SQL/LDAP plugins:
    - ``__setitem__`` receives the SCIM JSON document from ``data/users.py`` /
      ``data/groups.py``
    - ``__getitem__`` returns that document (with live MidPoint-mapped fields
      overlaid) for ``UserResource`` / ``GroupResource`` construction

    Mapped MidPoint fields:
    - Users: ``name`` ← userName, ``fullName`` ← displayName
    - Groups (as RoleType): ``name``/``displayName`` ← displayName;
      members ↔ role assignments

    The remainder of the SCIM document is stored in MidPoint ``description``,
    analogous to LDAP ``info`` / JumpCloud ``details``.
    """

    def __init__(self, resource_type: str, client: Optional[MidPointClient] = None):
        self.resource_type = resource_type
        self.description = f"MidPoint-{resource_type}"
        self.client = client or _client_from_env()
        self.endpoint = "users" if resource_type == self.USERS else "roles"
        self.wrapper = "user" if resource_type == self.USERS else "role"
        logger.info(
            "Initialized %s backend against %s",
            self.description,
            self.client.base_url,
        )

    def __iter__(self) -> Any:
        logger.debug("[__iter__]: %s", self.description)
        for obj in self.client.search(self.endpoint):
            if _parse_scim_details(obj.get(SCIM_DETAILS_PATH)):
                oid = obj.get("oid")
                if oid:
                    yield oid

    def __delitem__(self, id: str) -> None:
        logger.debug("[__delitem__]: %s, id=%s", self.description, id)
        if self.resource_type == self.GROUPS:
            for member in self.client.list_role_members(id):
                member_oid = member.get("oid")
                if member_oid:
                    try:
                        self.client.unassign_role(member_oid, id)
                    except Exception as exc:
                        logger.warning(
                            "Failed to unassign %s from %s: %s",
                            member_oid,
                            id,
                            exc,
                        )
        self.client.delete(self.endpoint, id)

    def __getitem__(self, id: str) -> Any:
        logger.debug("[__getitem__]: %s, id=%s", self.description, id)
        obj = self.client.get(self.endpoint, id)
        if not obj:
            return None

        resource = _parse_scim_details(obj.get(SCIM_DETAILS_PATH))
        if resource is None:
            return None

        # Overlay identity / indexed fields from MidPoint (same idea as LDAP).
        resource["id"] = obj.get("oid")
        if self.resource_type == self.USERS:
            resource["userName"] = _poly_name(obj.get("name"))
            resource["displayName"] = _poly_name(obj.get("fullName")) or resource.get(
                "displayName"
            )
        else:
            resource["displayName"] = (
                _poly_name(obj.get("displayName"))
                or _poly_name(obj.get("name"))
                or resource.get("displayName")
            )
            resource["members"] = self._read_members(id)

        logger.debug("[__getitem__] result keys: %s", list(resource.keys()))
        return resource

    def __setitem__(self, id: str, details: Any) -> None:
        logger.debug("[__setitem__]: %s, id=%s", self.description, id)
        resource = json.loads(details)
        if self.resource_type == self.USERS:
            self._write_user(id, resource)
        else:
            self._write_group(id, resource)

    def _write_user(self, oid: str, resource: dict) -> None:
        user_name = resource.pop("userName", None)
        display_name = resource.pop("displayName", None)
        if not user_name:
            raise Exception("Missing userName")

        payload = {
            "name": user_name,
            "fullName": display_name or user_name,
            SCIM_DETAILS_PATH: json.dumps(resource),
        }
        name = resource.get("name") or {}
        if isinstance(name, dict):
            if name.get("givenName"):
                payload["givenName"] = name["givenName"]
            if name.get("familyName"):
                payload["familyName"] = name["familyName"]

        existing = self.client.get("users", oid)
        if not existing:
            payload["oid"] = oid
            self.client.create("users", "user", payload)
            return

        deltas = [
            {"modificationType": "replace", "path": "name", "value": payload["name"]},
            {
                "modificationType": "replace",
                "path": "fullName",
                "value": payload["fullName"],
            },
            {
                "modificationType": "replace",
                "path": SCIM_DETAILS_PATH,
                "value": payload[SCIM_DETAILS_PATH],
            },
        ]
        if "givenName" in payload:
            deltas.append(
                {
                    "modificationType": "replace",
                    "path": "givenName",
                    "value": payload["givenName"],
                }
            )
        if "familyName" in payload:
            deltas.append(
                {
                    "modificationType": "replace",
                    "path": "familyName",
                    "value": payload["familyName"],
                }
            )
        self.client.patch("users", oid, deltas)

    def _write_group(self, oid: str, resource: dict) -> None:
        display_name = resource.pop("displayName", None) or oid
        members = resource.pop("members", []) or []

        payload = {
            "name": display_name,
            "displayName": display_name,
            SCIM_DETAILS_PATH: json.dumps(resource),
        }

        existing = self.client.get("roles", oid)
        if not existing:
            payload["oid"] = oid
            self.client.create("roles", "role", payload)
        else:
            self.client.patch(
                "roles",
                oid,
                [
                    {
                        "modificationType": "replace",
                        "path": "name",
                        "value": display_name,
                    },
                    {
                        "modificationType": "replace",
                        "path": "displayName",
                        "value": display_name,
                    },
                    {
                        "modificationType": "replace",
                        "path": SCIM_DETAILS_PATH,
                        "value": payload[SCIM_DETAILS_PATH],
                    },
                ],
            )

        self._sync_members(oid, members)

    def _sync_members(self, role_oid: str, members: List[dict]) -> None:
        desired = {
            member.get("value")
            for member in members
            if isinstance(member, dict) and member.get("value")
        }
        current = {
            member.get("oid")
            for member in self.client.list_role_members(role_oid)
            if member.get("oid")
        }

        for user_oid in sorted(desired - current):
            if not self.client.get("users", user_oid):
                raise Exception(f"Member: '{user_oid}' not existing")
            self.client.assign_role(user_oid, role_oid)

        for user_oid in sorted(current - desired):
            self.client.unassign_role(user_oid, role_oid)

    def _read_members(self, role_oid: str) -> List[dict]:
        members = []
        for user in self.client.list_role_members(role_oid):
            user_oid = user.get("oid")
            # Prefer SCIM displayName from stored user details when present.
            details = _parse_scim_details(user.get(SCIM_DETAILS_PATH)) or {}
            display = details.get("displayName") or _poly_name(user.get("fullName")) or _poly_name(
                user.get("name")
            )
            members.append(
                {
                    "value": user_oid,
                    "display": display,
                    "$ref": f"/Users/{user_oid}",
                }
            )
        return members
