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
          'Accept' : 'application/json',
          'x-api-key': self.key
        }

        if data:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(data)
            logger.debug(data)

        r = requests.request(method, url="{}{}".format(self.url, request), headers=headers, data=data)

        if r.status_code in [200, 201, 204]:
           try:
              return json.loads(r.text)
           except:
              return r.text
        else:
           logger.debug("API: {} {} returns: {} {}".format(method, request, r.status_code, r.text))

      except Exception as e:
        logger.error("API Exception: {}".format(str(e)))

      return None


    def users(self):
      for record in self.api(f"/api/systemusers").get('results', []) or []:
        logger.info(f"[user record]: {record}...")
        yield record['id']
  

    def groups(self):
      for record in self.api(f"/api/v2/usergroups") or []:
        logger.info(f"[group record]: {record}...")
        yield record['id']
  

    def lookup_user(self, username):
      record = self.api(f"/api/systemusers?filter=username:$eq:{username}")
      if not record:
        return None
      if record['totalCount'] != 1:
        raise Exception(f"Lookup or user: {username} returns: {record['totalCount']}")
      
      return record['results'][0]


    def lookup_group(self, groupname):
      record = self.api(f"/api/v2/usergroups?filter=usergroups:$eq:{groupname}")
      if not record:
        return None
      if record['totalCount'] != 1:
        raise Exception(f"Lookup or group: {groupname} returns: {record['totalCount']}")
      
      return record['results'][0]


    def read_user(self, id):
      logger.debug(f"[read_user] id: {id}...")

      record = self.api(f"/api/systemusers/{id}")
      if not record:
        return None
      
      displayname = record.get('displayname')
      if not displayname or displayname == '':
        displayname = f"{record['firstname']} {record['lastname']}"

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
        'externalId': record['external_dn'],
        'displayName': displayname,
        'name': {
          'givenName': record['firstname'],
          'familyName': record['lastname']
        },
        '509Certificates': [],
        'meta': {
          'location': f"/Users/{id}",
          'resourceType': 'User'
        }
      } # | record['attributes']

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
      record = self.api(f"/api/v2/usergroups/{id}")

      return {
        'id': id,
        'displayName': record['name'],
        'members': [],
        'meta': {
          'location': f"/Groups/{id}",
          'resourceType': 'Group'
        }      
      } | record['attributes']


    def write_user(self, id, details):
      
      ssh_keys = []
      for k in details.pop('509Certificates'):
        try:
          _, public_key, name = k.strip().split(' ')
          ssh_keys.append({ 'public_key': public_key, 'name': name })
        except:
          pass

      username = details.pop('userName')
      if not username or username == '':
        raise Exception("Missing username")

      name = details.pop('name')
      if not name:
        raise Exception('Missing name')

      firstname = name.pop('givenName')
      if not firstname or firstname == '':
        raise Exception("Missing firstname")

      lastname = name.pop('familyName')
      if not lastname or lastname == '':
        raise Exception("Missing lastname")

      email = details.pop('email')
      if not email or email == '':
        raise Exception("User: {} {} is not registered as JumpCloud user, since he is not having an email address".format(firstname, lastname))

      try:
        record = self.lookup_user(username)
        id = record['id']
        if record['email'] != email:
          raise Exception("User: {} {} has conflicting email adresseses: {} versus {}".format(firstname, lastname, email, record['email']))
      except:
        record = None

      if record:
        if not equal(firstname, record['firstname']) or not equal(lastname, self.record['lastname']):
          logger.debug("Updating person: {} {}".format(firstname, lastname))

          self.api('/api/systemusers/{}'.format(
              id,
              method='PUT',
              data={
                'firstname': firstname,
                'lastname': lastname,
                'attributes': details
              }
            )
          )

      else:
          logger.debug("Adding person: {} {}".format(firstname, lastname))

          try:
            record = self.api(
              '/api/systemusers',
              method='POST',
              data={
                'username': username,
                'email': email,
                'firstname': firstname,
                'lastname': lastname,
                'attributes': details
              }
            )
        
            id = record.get('_id')
          except:
            raise Exception("Cannot add user: {}".format(email))

  
      # Check our src keys, add the one that do not yet exist...
      for src_key in ssh_keys:
        exists = False

        for dst_key in self.persons[uid]['record']['ssh_keys']:
          if equal(src_key['public_key'], dst_key['public_key']):
            exists = True
            break

        if not exists:
          logger.debug("Adding SSH key {}".format(src_key['name']))

          self.api('/api/systemusers/{}/sshkeys'.format(id), method='POST', data = {
             'public_key': src_key['public_key'],
             'name': src_key['name']
            }
          )

      # Check the existing keys, delete the ones that are no longer valid...
      for dst_key in self.persons[uid]['record']['ssh_keys']:
        valid = False

        for src_key in ssh_keys:
          
          if equal(src_key['public_key'], dst_key['public_key']):
            valid = True
            break

        if not valid:
          logger.debug("Delete SSH key {}".format(dst_key['name']))
          
          self.api('/api/systemusers/{}/sshkeys/{}'.format(id, dst_key['id']), method='DELETE')

      return self


    def write_group(self, id, members):

      record = self.lookup_group(id)

      if not record:
        logger.debug("Group {} does not yet exist".format(name))

        record = self.api('/api/v2/usergroups', method='POST', data = {
            'name': groupname
          }
        )

        id = record['id']

      for memberUid in members:
        uid = self.lookup_person(memberUid)

        if not uid:
          logger.debug("member: {} is not registered as JumpCloud group member, since he is not a valid JumpCloud person".format(memberUid))
          continue

        if uid not in self.groups[gid]['members']:
          logger.debug("Adding {} to group {}".format(uid, gid))

          self.api('/api/v2/usergroups/{}/members'.format(id), method='POST', data = {
              "op": "add", "type": "user", "id": uid
            }
          )

        return self


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
        self.jumpcloud.write_user(id, details)
      elif self.resource_type == "Groups":
        self.jumpcloud.write_group(id, details)
