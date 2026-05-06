# routers/__init__.py

import time
import json
import re
try:
    import pika
except ImportError:
    pika = None

from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute

from schema import SCIM_API_MESSAGES, SCIM_CONTENT_TYPE, ListResponse

from filter import Filter
from typing import Callable, Any

from data.users import get_user_resources
from data.groups import get_group_resources

import os
import logging

logger = logging.getLogger(__name__)

BASE_PATH = os.environ.get('BASE_PATH', '')
PAGE_SIZE = int(os.environ.get('PAGE_SIZE', 100))
REDACTED_KEYS = {
    "password",
    "token",
    "secret",
    "authorization",
    "access_token",
    "refresh_token",
    "client_secret",
    "api_key",
    "x-api-key",
}


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for k, v in value.items():
            if str(k).lower() in REDACTED_KEYS:
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = _redact_sensitive(v)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(v) for v in value]
    return value


def redact_request_body(raw_body: str) -> str:
    if not raw_body:
        return raw_body
    try:
        parsed = json.loads(raw_body)
        return json.dumps(_redact_sensitive(parsed))
    except Exception:
        return raw_body


def broadcast(data: Any) -> None:

    AMQP = os.environ.get('AMQP', None)
    QUEUE = os.environ.get('QUEUE', 'SCIM')

    if not AMQP:
        return

    if pika is None:
        logger.warning("AMQP configured but pika is not installed; skipping broadcast")
        return

    try:
        parameters = pika.URLParameters(AMQP)
        connection = pika.BlockingConnection(parameters)
    except Exception as e:
        logger.error(f"Exception connecting to: {AMQP}, error: {str(e)}")
        return

    channel = connection.channel()

    channel.queue_declare(
        queue=QUEUE,
        durable=True
    )

    logger.debug(f"Broadcasting: {QUEUE}, data: {json.dumps(data)}")

    channel.basic_publish(
        exchange='',
        routing_key=QUEUE,
        body=json.dumps(data),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
        )
    )

    connection.close()


class SCIM_Response(Response):
    media_type = SCIM_CONTENT_TYPE

    def render(self, content: Any) -> bytes:
        return json.dumps(content).encode()


class SCIM_Route(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        def verify_content_type(direction, headers):
            if int(headers.get('content-length', 0)) > 0:
                if headers.get('content-type', '') != SCIM_CONTENT_TYPE:
                    logger.error(
                        f"content-type in {direction} "
                        f"should be: {SCIM_CONTENT_TYPE}")

        async def custom_route_handler(request: Request) -> Response:
            before = time.time()
            request_body_text = ""
            body_methods = {"POST", "PUT", "PATCH", "DELETE"}

            if request.method in body_methods and logger.isEnabledFor(logging.DEBUG):
                try:
                    # FastAPI caches request.body(), so downstream handlers can still read it.
                    request_body_text = (await request.body()).decode(
                        "utf-8",
                        errors="replace"
                    )
                    request_body_text = redact_request_body(request_body_text)
                except Exception:
                    request_body_text = "<unreadable>"

            verify_content_type('request', request.headers)

            try:
                response: Response = await original_route_handler(request)
            except HTTPException as exc:
                logger.error(
                    "[REQ FAIL] %s %s status=%s detail=%s content_type=%s body=%s",
                    request.method,
                    request.url.path,
                    exc.status_code,
                    exc.detail,
                    request.headers.get("content-type", ""),
                    request_body_text[:4000]
                )
                raise
            except Exception as exc:
                logger.exception(
                    "[REQ FAIL] %s %s status=500 detail=%s content_type=%s body=%s",
                    request.method,
                    request.url.path,
                    str(exc),
                    request.headers.get("content-type", ""),
                    request_body_text[:4000]
                )
                raise
            duration = time.time() - before
            response.headers["X-Response-Time"] = str(duration)

            if response.status_code >= 400:
                logger.error(
                    "[REQ FAIL] %s %s status=%s content_type=%s body=%s",
                    request.method,
                    request.url.path,
                    response.status_code,
                    request.headers.get("content-type", ""),
                    request_body_text[:4000]
                )

            verify_content_type('response', response.headers)

            return response

        return custom_route_handler


reader = {
    'User': get_user_resources,
    'Group': get_group_resources,
}


def get_all_resources(
    resource_type, startindex, count, query
) -> ListResponse:
    """ Read all resource of resource type"""

    try:
        resource_reader = reader.get(resource_type)
        if not resource_reader:
            raise Exception(f"No reader for: {resource_type}")

        startindex = max(1, startindex)
        count = max(0, count)

        totalresults = (
            resource_reader(
                Filter(query)
            ) or []
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    resources = totalresults[startindex-1:][:count]

    return ListResponse(
        Resources=resources,
        itemsPerPage=len(resources),
        schemas=[
            SCIM_API_MESSAGES+":ListResponse"
        ],
        startIndex=startindex,
        totalResults=len(totalresults)
    )


def patch_resource(resource, operations):
    def _split_path(path: str):
        if not path:
            return []
        return [part for part in path.split('.') if part]

    def _get_parent_and_key(obj, path: str):
        parts = _split_path(path)
        if not parts:
            raise HTTPException(status_code=400, detail="Patch path is required")

        current = obj
        for part in parts[:-1]:
            if not isinstance(current, dict):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot traverse non-object path: {path}"
                )
            if part not in current or current[part] is None:
                current[part] = {}
            elif not isinstance(current[part], dict):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot traverse non-object path: {path}"
                )
            current = current[part]

        return current, parts[-1]

    def _get_value(obj, path: str):
        current = obj
        for part in _split_path(path):
            if not isinstance(current, dict) or part not in current:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot access non-existing: {path}"
                )
            current = current[part]
        return current

    def _set_value(obj, path: str, value):
        parent, key = _get_parent_and_key(obj, path)
        parent[key] = value

    def _remove_value(obj, path: str):
        # RFC7644 valuePath support (e.g. members[value eq "user-id"])
        filtered_match = re.fullmatch(
            r'([A-Za-z0-9_.$-]+)\[\s*([A-Za-z0-9_.$-]+)\s+eq\s+"([^"]+)"\s*\]',
            path or ""
        )
        if filtered_match:
            list_path, attr_name, expected = filtered_match.groups()
            target_list = _get_value(obj, list_path)
            if not isinstance(target_list, list):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot remove from non-list: {list_path}"
                )

            filtered_list = [
                item for item in target_list
                if not (
                    isinstance(item, dict) and
                    str(item.get(attr_name)) == expected
                )
            ]
            _set_value(obj, list_path, filtered_list)
            return

        parent, key = _get_parent_and_key(obj, path)
        if key not in parent:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot remove non-existing: {path}"
            )
        parent.pop(key)

    for operation in operations:
        if operation.op.upper() == 'REMOVE':
            _remove_value(resource, operation.path)
        elif operation.op.upper() == 'REPLACE':
            _set_value(resource, operation.path, operation.value)
        elif operation.op.upper() == 'ADD':
            value_at_path = None
            path_exists = True
            try:
                value_at_path = _get_value(resource, operation.path)
            except HTTPException:
                path_exists = False

            if path_exists:
                if isinstance(value_at_path, list):
                    if isinstance(operation.value, list):
                        items_to_add = operation.value
                    else:
                        items_to_add = [operation.value]

                    for new_item in items_to_add:
                        if not isinstance(new_item, dict):
                            if new_item not in value_at_path:
                                value_at_path.append(new_item)
                            continue

                        # If new_item is a dict, check if it already exists
                        # based on the key attributes of the new_item
                        item_exists = False

                        keys = new_item.keys()

                        for existing_item in value_at_path:
                            for key in keys:
                                if (
                                    key in new_item and
                                    key in existing_item and
                                    existing_item[key] == new_item[key]
                                ):
                                    item_exists = True
                                    break

                            if item_exists:
                                break

                        # Add the item if it doesn't exist
                        if not item_exists:
                            value_at_path.append(new_item)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot add to non-list: {operation.path}"
                    )
            else:
                # If the path doesn't exist, create it with the value
                _set_value(resource, operation.path, operation.value)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown operation: {operation.op}"
            )

    logger.debug(f"[PATCH RESULT] {resource}")
    return resource


def resource_exists(resource_type, query) -> bool:
    return (get_all_resources(resource_type, 1, 1, query).totalResults > 0)
