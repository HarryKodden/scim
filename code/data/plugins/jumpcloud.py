import uuid
import json
import requests

from typing import Any
from data.plugins import Plugin

import logging
logger = logging.getLogger(__name__)


def equal(a, b):
    return (a.lower() == b.lower())


class JumpCloud(object):

    url = None
    key = None

    def __init__(self, url, key):
        self.url = url
        self.key = key

    def api(self, request, method='GET', data=None):

        print("API: {} {} ...".format(method, request))

        try:
            headers = {
                'Accept': 'application/json',
                'x-api-key': self.key
            }

            if data:
                headers['Content-Type'] = 'application/json'
                data = json.dumps(data)
                logger.debug(data)

            r = requests.request(
                method,
                url="{self.url}{request}",
                headers=headers,
                data=data
            )

            if r.status_code in [200, 201, 204]:
                try:
                    return json.loads(r.text)
                except Exception:
                    return r.text
            else:
                logger.debug(
                    f"API: {method} {request}"
                    f" --> {r.status_code} {r.text}"
                )

        except Exception as e:
            logger.error("API Exception: {}".format(str(e)))

        return None

    def users(self):
        for record in self.api("/api/systemusers").get('results', []) or []:
            logger.info(f"[user record]: {record}...")
            yield record['id']

    def groups(self):
        for record in self.api("/api/v2/usergroups") or []:
            logger.info(f"[group record]: {record}...")
            yield record['id']

    def create_user(self) -> str:
        record = self.api(
            '/api/systemusers',
            method='POST',
            data={
                'username': str(uuid.uuid4()),
                'activated': False,
                'email': 'noreply@none'
            }
        )

        return record.get('id')

    def create_group(self) -> str:
        record = self.api(
            '/api/v2/usergroups',
            method='POST',
            data={
                'name': str(uuid.uuid4())
            }
        )

        return record.get('id')

    def read_user(self, id):
        logger.debug(f"[read_user] id: {id}...")

        record = self.api(f"/api/systemusers/{id}")
        if not record:
            return None

        result = {
            'id': id,
            'active': not record['account_locked'],
            'emails': [
                {
                    'primary': True,
                    'value': record['email']
                }
            ],
            'userName': record['username'],
            'externalId': record.get('external_dn', None),
            'displayName': record.get('displayname', None),
            '509Certificates': [],
            'meta': {
                'location': f"/Users/{id}",
                'resourceType': 'User'
            }
        }

        firstname = record.get('firstname', None)
        lastname = record.get('lastname', None)
        if firstname or lastname:
            result |= {
                'name': {
                    'givenName': firstname,
                    'familyName': lastname
                }
            }

        for custom in record.get('attributes', []):
            if custom['name'] == 'details':
                result |= json.loads(custom['valuue'])

        for sshkey in self.api(f"/api/systemusers/{id}/sshkeys"):
            logger.debug(f"[sshkeys] sshkey: {sshkey}")

            result['509Certificates'].append(
                {
                    'value': sshkey['public_key']
                }
            )

        logger.info(result)

        return result

    def read_group(self, id):
        logger.debug(f"[read_group] id: {id}...")

        record = self.api(f"/api/v2/usergroups/{id}")
        if not record:
            return None

        members = []
        for m in self.read_members(id):
            members.append(
                {
                    'value': m
                }
            )

        return {
            'id': id,
            'displayName': record['name'],
            'members': members,
            'meta': {
                'location': f"/Groups/{id}",
                'resourceType': 'Group'
            }
        } | json.loads(record.get('attributes', {}).get('details', '{}'))

    def update_user(self, id, details):
        new_keys = []
        for key in details.pop('509Certificates', []):
            try:
                _, public_key, name = key.strip().split(' ')
                new_keys.append(
                    {
                        'public_key': public_key,
                        'name': name
                    }
                )
            except Exception as e:
                raise Exception(f"Processing X509Certificates: {str(e)}")

        username = details.pop('userName', None)
        if not username or username == '':
            raise Exception("Missing username")

        email = None
        for e in details.pop('emails', []):
            if e.get('primary', False):
                email = e.get('value', None)

            if email:
                break

        if not email or email == '':
            raise Exception(f"Missing email for uer {username}")

        data = {
            'username': username,
            'email': email
        }

        name = details.pop('name')
        if name:
            data['firstname'] = name.get('givenName', '')
            data['lastname'] = name.get('familyName', '')

        data['attributes'] = [
            {
                "name": "details",
                "value": json.dumps(details)
            }
        ]

        self.api(
            f'/api/systemusers/{id}',
            method='PUT',
        )

        # Check our src keys, add the one that do not yet exist...

        old_keys = self.api(f"/api/systemusers/{id}/sshkeys") or []

        for key in new_keys:
            exists = False

            for i in range(len(old_keys)):
                if equal(key['public_key'], old_keys[i]['public_key']):
                    old_keys = old_keys[:i] + old_keys[i+1:]
                    exists = True
                    break

            if not exists:
                logger.debug("Adding SSH key {}".format(key['name']))
                self.api(
                    f"/api/systemusers/{id}/sshkeys",
                    method='POST',
                    data={
                        'public_key': key['public_key'],
                        'name': key['name']
                    }
                )

        # Remove oldkeys that are no longer needed...
        for key in old_keys:
            logger.debug("Delete SSH key {}".format(key['name']))
            self.api(
                f"/api/systemusers/{id}/sshkeys/{key['id']}",
                method='DELETE'
            )

    def read_members(self, id):
        members = []

        skip = 0

        while True:
            result = self.api(
                f"/api/v2/usergroups/{id}/members?skip={skip}"
            ) or []
            if len(result) == 0:
                break

            skip += len(result)

            for m in result:
                if m['to']['type'] == 'user':
                    members.append(m['to']['id'])

        return members

    def update_members(self, id, new_members):
        old_members = self.read_members(id)

        # Add new members...
        for member in new_members:
            if not self.read_user(member['value']):
                logger.debug(
                    f"member: {member['value']} not knwon"
                )
                continue

            if member['value'] not in old_members:
                logger.debug(f"Adding {member['value']} to group {id}")

                self.api(
                    f"/api/v2/usergroups/{id}/members",
                    method='POST',
                    data={
                        "op": "add", "type": "user", "id": member['value']
                    }
                )
            else:
                old_members.remove(member['value'])

        # No longer members...
        for member in old_members:
            logger.debug("Deleting {member} from group {id}")

            self.api(
                f"/api/v2/usergroups/{id}/members",
                method='POST',
                data={
                    "op": "remove", "type": "user", "id": member
                }
            )

    def update_group(self, id, details):
        name = details.pop('displayName')
        members = details.pop('members', [])

        self.api(
            f"/api/v2/usergroups/{id}",
            method='PUT',
            data={
                'name': name,
                'attributes': {
                        "details": json.dumps(details)
                }
            }
        )

        self.update_members(id, members)

    def delete_user(self, id):
        self.api("/api/systemusers/{}".format(id), method='DELETE')

    def delete_group(self, id):
        self.api("/api/v2/usergroups/{}".format(id), method='DELETE')


class JumpCloudPlugin(Plugin):

    def __init__(
        self,
        resource_type: str,
        jumpcloud_url: str = "https://console.jumpcloud.com",
        jumpcloud_key: str = None
    ):
        if not jumpcloud_key:
            raise Exception("No JumpCloud token provided")

        self.resource_type = resource_type
        self.description = f"JumpCloud-{resource_type}"

        self.jumpcloud = JumpCloud(jumpcloud_url, jumpcloud_key)

    def id(self) -> Any:
        logger.debug(f"[id]: {self.description}")

        if self.resource_type == "Users":
            return self.jumpcloud.create_user()
        elif self.resource_type == "Groups":
            return self.jumpcloud.create_group()

    def __iter__(self) -> Any:
        logger.debug(f"[__iter__]: {self.description}")

        if self.resource_type == "Users":
            for id in self.jumpcloud.users():
                yield id

        elif self.resource_type == "Groups":
            for id in self.jumpcloud.groups():
                yield id

    def __delitem__(self, id: str) -> None:
        logger.debug(f"[__delitem__]: {self.description}, id:{id}")

        if self.resource_type == "Users":
            self.jumpcloud.delete_user(id)
        elif self.resource_type == "Groups":
            self.jumpcloud.delete_group(id)

    def __getitem__(self, id: str) -> Any:
        logger.debug(f"[__getitem__]: {self.description}, id:{id}")

        if self.resource_type == "Users":
            return self.jumpcloud.read_user(id)
        elif self.resource_type == "Groups":
            return self.jumpcloud.read_group(id)

    def __setitem__(self, id: str, details: Any) -> None:
        logger.debug(
            f"[__setitem__]: {self.description}, id:{id}, details: {details}"
        )

        if self.resource_type == "Users":
            self.jumpcloud.update_user(id, json.loads(details))
        elif self.resource_type == "Groups":
            self.jumpcloud.update_group(id, json.loads(details))
