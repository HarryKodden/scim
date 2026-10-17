import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from data.plugins import Plugin

logger = logging.getLogger(__name__)

# SCIM document (after mapped native attrs are popped) lives in a MidPoint
# schema-extension attribute — not in the human-facing ``description`` field.
# Deploy a SchemaType that defines this item on UserType and RoleType (hidden
# in the GUI). See midpoint-invite-integration post-initial-objects.
#
# Override with env if your schema uses another namespace / local name / path.
SCIM_DETAILS_NS = os.environ.get(
    "MIDPOINT_SCIM_EXTENSION_NS",
    "https://github.com/HarryKodden/scim/xml/ns/midpoint",
)
SCIM_DETAILS_ATTR = os.environ.get("MIDPOINT_SCIM_EXTENSION_ATTR", "scimResource")
# Optional full Prism path override (e.g. "extension/scim:scimResource").
SCIM_DETAILS_PATH = os.environ.get(
    "MIDPOINT_SCIM_DETAILS_PATH",
    f"extension/{SCIM_DETAILS_ATTR}",
)
# Legacy storage location — still read for migration of older objects.
_LEGACY_SCIM_DETAILS_PATH = "description"


# MidPoint-leading mode: Invite may echo SCIM Group create/delete after we
# create/delete the Role in Invite via API. Match Groups to existing Roles by
# name; never delete MidPoint Roles on SCIM Group DELETE.
def _midpoint_leading_groups() -> bool:
    return os.environ.get("MIDPOINT_LEADING_GROUPS", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


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
    # Generic SCIM resources always carry schemas; reject unrelated free text.
    if "schemas" not in data:
        return None
    return data


def _extension_item_value(extension: Any, attr: str, ns: str) -> Any:
    """Pull ``attr`` out of a MidPoint ``extension`` JSON object (any ns form)."""
    if not isinstance(extension, dict):
        return None
    if attr in extension:
        return extension[attr]
    for key, value in extension.items():
        if key.startswith("@"):
            continue
        if key.endswith(f":{attr}") or key.endswith(f"#{attr}"):
            return value
        if key == ns and isinstance(value, dict) and attr in value:
            return value[attr]
        if isinstance(value, dict) and attr in value:
            # Nested map under an @ns / URI key we did not match above.
            nested_ns = value.get("@ns")
            if nested_ns in (None, ns):
                return value[attr]
    return None


def _get_scim_details_raw(obj: dict) -> Any:
    """Raw SCIM JSON string from extension (preferred) or legacy description."""
    raw = _extension_item_value(
        obj.get("extension"), SCIM_DETAILS_ATTR, SCIM_DETAILS_NS
    )
    if raw:
        return raw
    return obj.get(_LEGACY_SCIM_DETAILS_PATH)


def _extension_write_payload(scim_json: str) -> dict:
    """Nested ``extension`` fragment for MidPoint create/replace payloads."""
    return {
        "@ns": SCIM_DETAILS_NS,
        SCIM_DETAILS_ATTR: scim_json,
    }


def _scim_details_replace_delta(scim_json: str) -> dict:
    return {
        "modificationType": "replace",
        "path": SCIM_DETAILS_PATH,
        "value": scim_json,
    }


def _legacy_description_cleanup_delta(obj: Optional[dict]) -> Optional[dict]:
    """If ``description`` still holds a SCIM blob, clear it after migrating."""
    if not obj:
        return None
    if not _parse_scim_details(obj.get(_LEGACY_SCIM_DETAILS_PATH)):
        return None
    return {
        "modificationType": "replace",
        "path": _LEGACY_SCIM_DETAILS_PATH,
        "value": "",
    }


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

    def find_role_by_name(self, name: str) -> Optional[dict]:
        """Return the first RoleType whose name equals ``name``, if any."""
        if not name:
            return None
        # Escape quotes in names for MidPoint filter text.
        safe = name.replace("\\", "\\\\").replace('"', '\\"')
        roles = self.search("roles", f'name = "{safe}"')
        return roles[0] if roles else None

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

    The remainder of the SCIM document is stored in MidPoint extension
    attribute ``scimResource`` (see ``SCIM_DETAILS_*``), analogous to LDAP
    ``info`` / JumpCloud ``details``. Legacy objects may still carry the blob
    in ``description``; reads fall back there and writes migrate it away.
    """

    def __init__(self, resource_type: str, client: Optional[MidPointClient] = None):
        self.resource_type = resource_type
        self.description = f"MidPoint-{resource_type}"
        self.client = client or _client_from_env()
        self.endpoint = "users" if resource_type == self.USERS else "roles"
        self.wrapper = "user" if resource_type == self.USERS else "role"
        logger.info(
            "Initialized %s backend against %s "
            "(leading_groups=%s, scim_details=%s ns=%s)",
            self.description,
            self.client.base_url,
            _midpoint_leading_groups(),
            SCIM_DETAILS_PATH,
            SCIM_DETAILS_NS,
        )

    def id(self, details: dict) -> str:
        """Prefer an existing MidPoint Role oid when Group displayName matches."""
        if self.resource_type == self.GROUPS and _midpoint_leading_groups():
            display = details.get("displayName") or details.get("externalId")
            if display:
                # Invite externalId is often a URN; Role name is displayName.
                name = details.get("displayName") or display
                existing = self.client.find_role_by_name(name)
                if existing and existing.get("oid"):
                    logger.info(
                        "SCIM Group id: reuse MidPoint Role %s for name=%s",
                        existing["oid"],
                        name,
                    )
                    return existing["oid"]
        return str(uuid.uuid4())

    def __iter__(self) -> Any:
        logger.debug("[__iter__]: %s", self.description)
        for obj in self.client.search(self.endpoint):
            if _parse_scim_details(_get_scim_details_raw(obj)):
                oid = obj.get("oid")
                if oid:
                    yield oid

    def __delitem__(self, id: str) -> None:
        logger.debug("[__delitem__]: %s, id=%s", self.description, id)
        if self.resource_type == self.GROUPS and _midpoint_leading_groups():
            logger.info(
                "SCIM Group DELETE %s: MidPoint-leading no-op "
                "(MidPoint Role is not deleted)",
                id,
            )
            return
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

        resource = _parse_scim_details(_get_scim_details_raw(obj))
        if resource is None:
            # MidPoint-native object (no SCIM blob). Still expose a minimal
            # SCIM resource so Group membership validation does not fail for
            # members assigned outside SCIM (e.g. MidPoint GUI / invite_bridge tests).
            name = _poly_name(obj.get("name")) or id
            if self.resource_type == self.USERS:
                resource = {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "userName": name,
                    "displayName": _poly_name(obj.get("fullName")) or name,
                }
            else:
                resource = {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                    "displayName": (
                        _poly_name(obj.get("displayName"))
                        or name
                    ),
                }
            logger.debug(
                "[__getitem__] synthesized SCIM resource for MidPoint-only %s %s",
                self.resource_type,
                id,
            )

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

        scim_json = json.dumps(resource)
        payload = {
            "name": user_name,
            "fullName": display_name or user_name,
            "extension": _extension_write_payload(scim_json),
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
            _scim_details_replace_delta(scim_json),
        ]
        cleanup = _legacy_description_cleanup_delta(existing)
        if cleanup:
            deltas.append(cleanup)
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

        scim_json = json.dumps(resource)
        payload = {
            "name": display_name,
            "displayName": display_name,
            "extension": _extension_write_payload(scim_json),
        }

        existing = self.client.get("roles", oid)
        if (
            not existing
            and _midpoint_leading_groups()
            and display_name
        ):
            # Invite echoes Group create with a new SCIM id; bind to MidPoint Role by name.
            by_name = self.client.find_role_by_name(display_name)
            if by_name and by_name.get("oid"):
                logger.info(
                    "SCIM Group write: Role %s already exists as %s — "
                    "update SCIM details only (no Role create)",
                    display_name,
                    by_name["oid"],
                )
                existing = by_name
                oid = by_name["oid"]

        if not existing:
            payload["oid"] = oid
            self.client.create("roles", "role", payload)
            self._sync_members(oid, members)
            return

        # Existing MidPoint Role: keep name stable in leading mode; store SCIM blob.
        deltas = [_scim_details_replace_delta(scim_json)]
        cleanup = _legacy_description_cleanup_delta(existing)
        if cleanup:
            deltas.append(cleanup)
        if not _midpoint_leading_groups():
            deltas.extend(
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
                ]
            )
        self.client.patch("roles", oid, deltas)

        # Invite Group *create* sends members:[]. Do not wipe MidPoint members.
        if members:
            self._sync_members(oid, members)
        elif _midpoint_leading_groups():
            current = self.client.list_role_members(oid)
            if current:
                logger.info(
                    "SCIM Group write %s: empty members ignored "
                    "(preserving %s MidPoint assignment(s))",
                    display_name,
                    len(current),
                )
            else:
                self._sync_members(oid, members)
        else:
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
            details = _parse_scim_details(_get_scim_details_raw(user)) or {}
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
