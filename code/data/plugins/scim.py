import json
import requests

from typing import Any
from schema import CORE_SCHEMA_GROUP, SCIM_CONTENT_TYPE

import logging
logger = logging.getLogger(__name__)


class SCIM_Forward_Plugin(object):

    def __init__(
        self,
        resource_type: str,
        url: str = None,
        key: str = None
    ):
        self.resource_type = resource_type
        self.url = url
        self.key = key
        self.description = f"SCIM-Forward-{resource_type}"

    def api(self, request, method='GET', data=None):

        logger.debug("API: {} {} ...".format(method, request))

        try:
            headers = {
                'Accept': SCIM_CONTENT_TYPE,
                'x-api-key': self.key
            }

            if data:
                headers['Content-Type'] = SCIM_CONTENT_TYPE
                data = json.dumps(data)
                logger.debug(f"[{method}] -- {request} DATA: {data}")

            r = requests.request(
                method,
                url=f"{self.url}{request}",
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

    def _resources(self):
        resources = []

        while True:
            response = self.api(
                f"/{self.resource_type}?startIndex={len(resources)+1}"
            )

            if "Resources" not in response:
                raise Exception(f"lookup resources {self.resource_type}")

            resources += response["Resources"]

            if response["totalResults"] == len(resources):
                break

        return resources

    def __iter__(self) -> Any:
        logger.debug(f"[__iter__]: {self.description}")

        for resource in self._resources():
            yield resource['id']

    def __delitem__(self, id: str) -> None:
        logger.debug(f"[__delitem__]: {self.description}, id:{id}")

        return self.api(f"/{self.resource_type}", method='DELETE')

    def __getitem__(self, id: str) -> Any:
        logger.debug(f"[__getitem__]: {self.description}, id:{id}")

        return self.api(f"/{self.resource_type}/{id}")

    def __setitem__(self, id: str, details: Any) -> None:
        logger.debug(
            f"[__setitem__]: {self.description}, id:{id}, details: {details}"
        )

        data = json.loads(details)

        members = []

        if self.resource_type == 'Groups':
            members = data.pop('members', [])
            data['members'] = []

        if id:
            self.api(
                f"/{self.resource_type}/{id}",
                method='PUT',
                data=data
            )
        else:
            resource = self.api(
                f"/{self.resource_type}",
                method='POST',
                data=data
            )
            id = resource["id"]

        if members:
            self.api(f"/{self.resource_type}/{id}", method='PATCH', data={
                "operations": [{
                    "op": "add",
                    "path": "members",
                    "value": members
                }],
                "schemas": [CORE_SCHEMA_GROUP]
            })
