# events/publisher.py

"""Publish RFC 9967 provisioning events from router mutations."""

import json
import logging
from typing import Any, Dict, Literal, Optional, Union

from events.builder import ProvisioningOp, build_provisioning_event
from events.config import EventConfig, load_event_config
from events.delivery.push import deliver_set_push

logger = logging.getLogger(__name__)

ResourceType = Literal["User", "Group"]


def _resource_dict(resource: Any) -> Dict[str, Any]:
    if isinstance(resource, dict):
        return resource
    return json.loads(
        resource.model_dump_json(by_alias=True, exclude_none=True)
    )


def publish_provisioning_event(
    operation: ProvisioningOp,
    resource_type: ResourceType,
    resource: Any,
    *,
    patch_operations: Any = None,
    attributes: Optional[list] = None,
    config: Optional[EventConfig] = None,
    base_path: Optional[str] = None,
) -> bool:
    """
    Build and deliver a provisioning SET.

    Never raises — logs failures and returns False so SCIM writes are not rolled back.
    """
    cfg = config or load_event_config()
    if not cfg.push_enabled:
        logger.debug(
            "Provisioning event not delivered (SET_PUSH_URL unset): %s %s",
            operation,
            resource_type,
        )
        return False

    try:
        resource_data = _resource_dict(resource)
        set_token = build_provisioning_event(
            operation,
            resource_type,
            resource_data,
            attributes=attributes,
            config=cfg,
            patch_operations=patch_operations,
            base_path=base_path,
        )
        delivered = deliver_set_push(set_token, cfg)
        if not delivered:
            logger.warning(
                "Failed to deliver provisioning SET: op=%s type=%s uri=%s",
                operation,
                resource_type,
                resource_data.get("meta", {}).get("location"),
            )
        return delivered
    except Exception as exc:
        logger.error(
            "Error building/delivering provisioning SET: op=%s type=%s error=%s",
            operation,
            resource_type,
            str(exc),
        )
        return False


def emit_user_event(
    operation: ProvisioningOp,
    user: Any,
    *,
    patch_operations: Any = None,
    base_path: Optional[str] = None,
) -> bool:
    return publish_provisioning_event(
        operation,
        "User",
        user,
        patch_operations=patch_operations,
        base_path=base_path,
    )


def emit_group_event(
    operation: ProvisioningOp,
    group: Any,
    *,
    patch_operations: Any = None,
    base_path: Optional[str] = None,
) -> bool:
    return publish_provisioning_event(
        operation,
        "Group",
        group,
        patch_operations=patch_operations,
        base_path=base_path,
    )
