import os
import json
import logging

from typing import Any
from data.plugins import Plugin
from ldap3 import Server, Connection, ObjectDef, AttrDef, Reader, Writer, SUBTREE, ALL_ATTRIBUTES, ALL

logger = logging.getLogger(__name__)


class LDAP_Plugin(Plugin):

    def __init__(
        self,
        resource_type: str,
        ldap_hostname: str = None,
        ldap_username: str = None, 
        ldap_password: str = None
    ):
        self.resource_type = resource_type
        self.description = f'LDAP-{resource_type}'

        if resource_type == 'Users':
            self.resource_dn = self.user_dn()
        if resource_type == 'Groups':
            self.resource_dn = self.group_dn()
                
        logger.info("Connectinto to LDAP...")
        
        # Establish connection with LDAP...
        try:
            s = Server(ldap_hostname, get_info=ALL)

            self.session = Connection(s, user=ldap_username, password=ldap_password)
            if not self.session.bind():
               raise("Exception during bind")

            logger.debug("LDAP Connected !")
            logger.info(s.info)
        except Exception as e:
            logger.error("Problem connecting to LDAP {} error: {}".format(ldap_hostname, str(e)))

        self.document_def = ObjectDef(['document', 'extensibleObject'], self.session)
        self.document_def += AttrDef('info')

        if self.resource_type == 'Users':
            self.document_def += AttrDef('uid')
            self.document_def += AttrDef('displayName')
            self.document_def += AttrDef('sn')
            self.document_def += AttrDef('givenName')
            self.document_def += AttrDef('email')
            self.document_def += AttrDef('sshPublicKey')
            
        if  self.resource_type == 'Groups':
            self.document_def += AttrDef('displayName')
            self.document_def += AttrDef('member')

        self.session.add(
            self.resource_dn,
            attributes = {
                'objectClass': [
                    'organizationalUnit',
                    'top'
                ],
                'ou': self.resource_type
            }
        )

    @classmethod
    def user_dn(cls):
        return 'ou=Users'
        
    @classmethod
    def group_dn(cls):
        return 'ou=Groups'
    
    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        logger
        self.session.unbind()

    def search(self, 
        dn,
        scope=SUBTREE,
        filter="(objectclass=*)",
        attributes=[]
    ):
        result = {}

        g = self.session.extend.standard.paged_search(
            search_base = dn,
            search_filter = filter,
            search_scope = scope,
            attributes = attributes,
            paged_size = 100,
            generator=True
        )

        for i in g:
            result[i['dn']] = i['attributes']

        logger.info(result)

        return result

    def __iter__(self) -> Any:
        logger.debug(f"[__iter__]: {self.description}")

        reader = Reader(self.session, self.document_def, self.resource_dn).search()

        for entry in self.session.entries:
            yield entry.documentIdentifier
                
    def __delitem__(self, id: str) -> None:
        logger.debug(f"[__delitem__]: {self.description}, id={id}")

        self.session.delete(f"documentIdentifier={id},{self.resource_dn}")

    def read_resource(self, dn) -> Any:
        logger.debug(f"[read_resource]: {dn}")
        
        r = Reader(self.session, self.document_def, dn).search()
        
        if len(r) == 0:
            raise Exception(f"Entry '{dn}' not found")
        
        entry = r[0]
        
        resource = json.loads(str(entry.info))
        
        resource['id'] = str(entry.documentIdentifier)
        resource['displayName'] = str(entry.displayname) or '???'
             
        if self.resource_type == 'Users':
            resource['userName'] = str(entry.uid) or '???'
                         
            resource['name'] = {
                'familyName': str(entry.sn),
                'givenName': str(entry.givenName)
            }
            
            if 'email' in entry:
                primary = True
                for email in entry.email:
                    resource.setdefault('emails', []).append(
                        {
                            "primary": primary,
                            "value": str(email)
                        }
                    )
                    primary = False
                    
            if 'sshPublicKey' in entry:
                for sshPublicKey in entry.sshPublicKey:
                    resource.setdefault('x509Certificates', []).append(
                        {
                            "value": str(sshPublicKey)
                        }
                    )

        if self.resource_type == 'Groups':
            if 'member' in entry:
                for dn in entry.member:
                    member = self.read_resource(dn)
                    resource.setdefault('members', []).append(
                        {
                            "value": member['id'],
                            "display": member['displayName'],
                            "$ref": f"/Users/{member['id']}"
                        }
                    )
        
        logger.info(resource)
        
        return resource
    
    def write_resource(self, id: str, resource: Any) -> None:
        dn = f"documentIdentifier={id},{self.resource_dn}"

        logger.debug(f"[write_resource]: {id} --> {dn}")

        writer = Writer(self.session, self.document_def, self.resource_dn)
        
        entry = writer.new(dn)

        entry.documentIdentifier = id

        if self.resource_type == 'Users':
            entry.uid = resource.pop('userName')
            entry.displayName = resource.pop('displayName')
            
            entry.email.discard()
            for email in resource.pop('emails', []):
                entry.email += email.get('value')
                
            entry.sshPublicKey.discard()
            for pubkey in resource.pop('x509Certificates', []):
                entry.sshPublicKey += pubkey.get('value')
                
            name = resource.pop('name', {})
            entry.sn = name.get('familyName', '')
            entry.givenName = name.get('givenName', '')
                    
        if self.resource_type == 'Groups':
            entry.displayName = resource.pop('displayName')
            
            members = resource.pop('members')
            entry.members.discard()
            for m in members:
                dn, _ = self.lookup(user_dn(), m['value'])
                entry.members += dn

        entry.info = json.dumps(resource)

        writer.commit()

    def lookup(self, base:str, id: str) -> str:
        logger.debug(f"[lookup]: {self.description}, id={id}")
      
        result = self.search(
            base,
            filter=f"(documentIdentifier={id})",
            attributes=[]
        )

        if len(result.keys()) == 0:
            return None

        if len(result.keys()) > 1:
            raise Exception(f"More than 1 record found in {base}")

        return list(result)[0]
    
    def __getitem__(self, id: str) -> Any:
        logger.debug(f"[__getitem__]: {self.description}, id={id}")
      
        dn = self.lookup(self.resource_dn, id)
        
        if not dn:
            raise Exception("Resource {id} does not exists")
        
        resource = self.read_resource(dn)

        return resource

    def __setitem__(self, id: str, details: Any) -> None:
        logger.debug(
            f"[__setitem__]: {self.description}, id:{id}, details: {details}"
        )

        resource = json.loads(details)

        self.write_resource(id, resource)
        
