import json
import requests

from typing import Any
from schema import CORE_SCHEMA_GROUP, SCIM_CONTENT_TYPE
from data.plugins import Plugin

import logging
logger = logging.getLogger(__name__)


class NetBird(Plugin):

    def __init__(
        self,
        resource_type: str,
        url: str = None,
        token: str = None
    ):
        self.resource_type = resource_type
        self.url = url
        self.token = token
        self.description = f"NetBird-{resource_type}"

    def api(self, request, method='GET', data=None):

        logger.debug("API: {} {} ...".format(method, request))

        try:
            headers = {
                'Accept': 'application/json',
                'Authorization': f"Token {self.token}"
            }

            if data:
                headers['Content-Type'] = 'application/json'
                data = json.dumps(data)
                logger.debug(f"[{method}] -- {request} DATA: {data}")

            r = requests.request(
                method,
                url=f"{self.url}/api{request}",
                headers=headers,
                data=data
            )

            if r.status_code in [200, 201, 204]:
                try:
                    return json.loads(r.text)
                except Exception:
                    return r.text
            else:
                raise Exception(
                    f"API: {method} {request}"
                    f" --> {r.status_code} {r.text}"
                )

        except Exception as e:
            logger.error("API Exception: {}".format(str(e)))

        return None

    def _resources(self) -> Any:
        return self.api(f"/{self.resource_type.lower()}")

    def __iter__(self) -> Any:
        logger.debug(f"[__iter__]: {self.description}")

        for resource in self._resources():
            yield resource['id']

    def __delitem__(self, id: str) -> None:
        logger.debug(f"[__delitem__]: {self.description}, id:{id}")

        return self.api(f"/{self.resource_type.lower()}/{id}", method='DELETE')

    def __getitem__(self, id: str) -> Any:
        logger.debug(f"[__getitem__]: {self.description}, id:{id}")

        for resource in self._resources():
            logger.debug(f"[__getitem__]: resource: {resource}")
            if resource['id'] == id:
                if self.resource_type == 'Users':
                    return {
                        'id': id,
                        'userName': resource['name'] if resource['name'] != '' else id,
                        'active': (resource['status'] == 'active' and not resource['is_blocked']),
                        'meta': {
                            'location': f"/Users/{id}",
                            'resourceType': '/User'
                        }
                    }
                if self.resource_type == 'Groups':
                    return {
                        'id': id,
                        'displayName': resource['name'],
                        'meta': {
                            'location': f"/Groups/{id}",
                            'resourceType': '/Group'
                        }
                    }
                return resource

        return None

    def __setitem__(self, id: str, details: Any) -> None:
        logger.debug(
            f"[__setitem__]: {self.description}, id:{id}, details: {details}"
        )

        netbird = {}

        if self.resource_type == 'Users':
            netbird.update(
                {
                    'role': 'user',
                    'auto_groups': [],
                    'is_service_user': False,
                    'name': details['userName']
                }
            )

        if self.resource_type == 'Groups':
            netbird.update(
                {
                    'name': details['displayName']
                }
            )

        data = json.loads(details)

        if self[id]:
            self.api(
                f"/{self.resource_type.lower()}/{id}",
                method='PUT',
                data=data
            )
        else:
            self.api(
                f"/{self.resource_type.lower()}",
                method='POST',
                data=data
            )
