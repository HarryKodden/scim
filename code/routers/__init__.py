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


def broadcast(resource_type: str, operation: str, id: int) -> None:

    AMQP = os.environ.get('AMQP', None)

    if not AMQP:
        return

    try:
        parameters = pika.URLParameters(AMQP)
        connection = pika.BlockingConnection(parameters)
    except Exception as e:
        logger.error(f"Exception connecting to: {AMQP}, error: {str(e)}")
        return

    channel = connection.channel()

    queue = f"SCIM-{resource_type}-{operation}".upper()

    channel.queue_declare(
        queue=queue,
        durable=True
    )

    logger.debug(f"Broadcasting: {queue}, id: {id}")

    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=id
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

    def patch(path, value):
        logger.debug(f"[PATCH] {path} := {value}")

        resource[path] = value

    for operation in operations:
        if operation.op == 'remove':
            resource.pop(operation.path)
        else:
            patch(operation.path, operation.value)

    logger.debug(f"[PATCH RESULT] {resource}")
    return resource


def resource_exists(resource_type, query) -> bool:
    return (get_all_resources(resource_type, 1, 1, query).totalResults > 0)
