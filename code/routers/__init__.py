# routers/__init__.py

import time
import json
import pika

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


def broadcast(data: Any) -> None:

    AMQP = os.environ.get('AMQP', None)
    QUEUE = os.environ.get('QUEUE', 'SCIM')

    if not AMQP:
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

            verify_content_type('request', request.headers)

            response: Response = await original_route_handler(request)
            duration = time.time() - before
            response.headers["X-Response-Time"] = str(duration)

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

    for operation in operations:
        if operation.op.upper() == 'REMOVE':
            resource.pop(operation.path)
        elif operation.op.upper() == 'REPLACE':
            if operation.path in resource:
                resource[operation.path] = operation.value
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot replace non-existing: {operation.path}"
                )
        elif operation.op.upper() == 'ADD':
            if operation.path in resource:
                if isinstance(resource[operation.path], list):
                    if isinstance(operation.value, list):
                        items_to_add = operation.value
                    else:
                        items_to_add = [operation.value]

                    for new_item in items_to_add:
                        if not isinstance(new_item, dict):
                            if new_item not in resource[operation.path]:
                                resource[operation.path].append(new_item)
                            continue

                        # If new_item is a dict, check if it already exists
                        # based on the key attributes of the new_item
                        item_exists = False

                        keys = new_item.keys()

                        for existing_item in resource[operation.path]:
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
                            resource[operation.path].append(new_item)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot add to non-list: {operation.path}"
                    )
            else:
                # If the path doesn't exist, create it with the value
                resource[operation.path] = operation.value
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown operation: {operation.op}"
            )

    logger.debug(f"[PATCH RESULT] {resource}")
    return resource


def resource_exists(resource_type, query) -> bool:
    return (get_all_resources(resource_type, 1, 1, query).totalResults > 0)
