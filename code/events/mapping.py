# events/mapping.py

"""SCIM event URI constants (RFC 9967). Wired in Phase 1."""

SCIM_EVENT_PREFIX = "urn:ietf:params:scim:event"

# Provisioning events (notice / full)
PROV_CREATE_NOTICE = f"{SCIM_EVENT_PREFIX}:prov:create:notice"
PROV_CREATE_FULL = f"{SCIM_EVENT_PREFIX}:prov:create:full"
PROV_PATCH_NOTICE = f"{SCIM_EVENT_PREFIX}:prov:patch:notice"
PROV_PATCH_FULL = f"{SCIM_EVENT_PREFIX}:prov:patch:full"
PROV_PUT_NOTICE = f"{SCIM_EVENT_PREFIX}:prov:put:notice"
PROV_PUT_FULL = f"{SCIM_EVENT_PREFIX}:prov:put:full"
PROV_DELETE = f"{SCIM_EVENT_PREFIX}:prov:delete"
PROV_ACTIVATE = f"{SCIM_EVENT_PREFIX}:prov:activate"
PROV_DEACTIVATE = f"{SCIM_EVENT_PREFIX}:prov:deactivate"

# Feed events (Phase 3)
FEED_ADD = f"{SCIM_EVENT_PREFIX}:feed:add"
FEED_REMOVE = f"{SCIM_EVENT_PREFIX}:feed:remove"

# Miscellaneous
MISC_ASYNC_RESP = f"{SCIM_EVENT_PREFIX}:misc:asyncresp"

# Default URIs advertised once Phase 1 notice mode is implemented
DEFAULT_NOTICE_EVENT_URIS = [
    PROV_CREATE_NOTICE,
    PROV_PATCH_NOTICE,
    PROV_PUT_NOTICE,
    PROV_DELETE,
]

LEGACY_OPERATION_TO_METHOD = {
    "Create": "POST",
    "Update": "PUT",
    "Delete": "DELETE",
}
