from datetime import datetime
from task_runner import RESPOURCE_TYPE_USER, call_change_webhook

import logging
import os
from unittest.mock import patch

logger = logging.getLogger(__name__)


@patch("task_runner.requests")
def test_call_change_webhook(setup_data):
    os.environ['SCIM_CHANGE_WEBHOOK_URL'] = "https://SCIM_CHANGE_WEBHOOK_URL"
    os.environ['SCIM_CHANGE_WEBHOOK_SECRET'] = "SCIM_CHANGE_WEBHOOK_SECRET"

    call_change_webhook({
        "datetime": datetime.now(),
        "name": "name"
      }, "create", RESPOURCE_TYPE_USER)
