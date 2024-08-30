from datetime import datetime
import json
import logging
import os

import requests
from huey.contrib.sql_huey import SqlHuey


logger = logging.getLogger(__name__)


USER_CHANGE_TYPE = "user"
GROUP_CHANGE_TYPE = "group"

CHANGE_TYPE_CREATE = "CREATE"
CHANGE_TYPE_UPDATE = "UPDATE"
CHANGE_TYPE_DELETE = "DELETE"


DATABASE_URL = os.environ.get("DATABASE_URL", "")


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON Encoder to handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)


if DATABASE_URL:
    huey = SqlHuey(database=DATABASE_URL)
else:
    huey = None
    logger.warning("DATABASE_URL is not set. Huey tasks will not be executed.")

if huey:
    @huey.task
    def call_change_webhook_task(
        obj: dict, action: str, resource_type: str
    ) -> None:  # pragma: no cover
        """
        Call webhook for user or group changes.
        """
        call_change_webhook(obj, action, resource_type)
else:
    def call_change_webhook_task(
        obj: dict, action: str, resource_type: str
    ) -> None:
        """
        Fallback function when DATABASE_URL is not set.
        This will simply call the webhook without queuing the task.
        """
        logger.warning("Huey is disabled. Calling webhook directly.")
        call_change_webhook(obj, action, resource_type)


def call_change_webhook(
    obj: dict, action: str, resource_type: str
) -> None:
    """
    Call webhook for user or group changes.
    """
    webhook_url = os.environ.get("SCIM_CHANGE_WEBHOOK_URL")
    webhook_secret = os.environ.get("SCIM_CHANGE_WEBHOOK_SECRET")
    if not (webhook_url) or not (webhook_secret):
        return

    obj["resource_type"] = resource_type.lower()
    obj["action"] = action.lower()

    headers = {
        "Content-Type": "application/json",
        "Authorization": webhook_secret,
    }
    try:
        logger.debug(f"{resource_type} <| {action} |> {obj}")
        logger.debug(f"Calling {resource_type} change webhook {webhook_url}")
        json_data = json.dumps(obj, cls=DateTimeEncoder)
        response = requests.post(
            headers=headers, json=json_data, url=webhook_url
        )
        response.raise_for_status()
    except Exception as ex:
        logger.exception("Error in calling the webhook", exc_info=ex)
