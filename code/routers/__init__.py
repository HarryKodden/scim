# routers/__init__.py

import time
import json

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


class SCIM_Response(Response):
    media_type = SCIM_CONTENT_TYPE

    def render(self, content: Any) -> bytes:
        return json.dumps(content).encode()


class SCIM_Route(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        def verify_content_type(direction, headers):
            if 'content-type' in headers and \
               'content-length' in headers and \
               int(headers['content-length']) > 0:
                if headers['content-type'] != SCIM_CONTENT_TYPE:
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
    # TODO: Apply operations on resource...
    return resource


def resource_exists(resource_type, query) -> bool:
    return (get_all_resources(resource_type, 1, 1, query).totalResults > 0)
