import json
import logging

from typing import Any
from data.plugins import Plugin
from ldap3 import Server, Connection, \
    ObjectDef, \
    AttrDef, Reader, Writer, \
    SUBTREE, ALL

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

        if resource_type == self.USERS:
            self.resource_dn = self.user_dn()
        if resource_type == self.GROUPS:
            self.resource_dn = self.group_dn()

        logger.info("Connectinto to LDAP...")

        # Establish connection with LDAP...
        try:
            server = Server(ldap_hostname, get_info=ALL)

            self.session = Connection(
                server,
                user=ldap_username,
                password=ldap_password
            )
            if not self.session.bind():
                raise Exception("Exception during bind")

            logger.debug("LDAP Connected !")
            logger.info(server.info)
        except Exception as e:
            logger.error(
                "Problem connecting to LDAP {} error: {}".format(
                    ldap_hostname,
                    str(e)
                )
            )
        if self.resource_type == self.USERS:
            self.document_def = ObjectDef(
                ['device', 'extensibleObject'],
                self.session
            )
            self.document_def += AttrDef('cn')
            self.document_def += AttrDef('uid')
            self.document_def += AttrDef('displayName')
            self.document_def += AttrDef('email')
            self.document_def += AttrDef('sshPublicKey')
            self.document_def += AttrDef('info')

        if self.resource_type == self.GROUPS:
            self.document_def = ObjectDef(
                ['device', 'extensibleObject'],
                self.session
            )
            self.document_def += AttrDef('cn')
            self.document_def += AttrDef('displayName')
            self.document_def += AttrDef('member')
            self.document_def += AttrDef('info')

        try:
            self.session.add(
                self.resource_dn,
                attributes={
                    'objectClass': [
                        'organizationalUnit',
                        'top'
                    ],
                    'ou': self.resource_type
                }
            )
        except Exception as e:
            logger.debug(f"OU {self.resource_type} may already exist: {e}")

    @classmethod
    def user_dn(cls):
        return 'ou=Users'

    @classmethod
    def group_dn(cls):
        return 'ou=Groups'

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.session.unbind()

    def search(
        self,
        dn,
        scope=SUBTREE,
        filter="(objectclass=*)",
        attributes=[]
    ):
        result = {}

        g = self.session.extend.standard.paged_search(
            search_base=dn,
            search_filter=filter,
            search_scope=scope,
            attributes=attributes,
            paged_size=100,
            generator=True
        )

        for i in g:
            result[i['dn']] = i['attributes']

        return result

    def __iter__(self) -> Any:
        logger.debug(f"[__iter__]: {self.description}")

        reader = Reader(self.session, self.document_def, self.resource_dn)
        reader.search()

        for record in reader:
            yield record.cn.value

    def __delitem__(self, id: str) -> None:
        logger.debug(f"[__delitem__]: {self.description}, id={id}")

        self.session.delete(f"cn={id},{self.resource_dn}")

    def read_resource(self, dn) -> Any:
        logger.debug(f"[read_resource]: {dn}")

        reader = Reader(self.session, self.document_def, dn)
        reader.search()

        if len(reader) == 0:
            raise Exception(f"record '{dn}' not found")

        record = reader[0]

        resource = json.loads(record.info.value)

        resource['id'] = record.cn.value
        resource['displayName'] = record.displayname.value

        if self.resource_type == self.USERS:
            resource['userName'] = record.uid.value

            if 'email' in record:
                primary = True
                for email in record.email:
                    resource.setdefault('emails', []).append(
                        {
                            "primary": primary,
                            "value": email
                        }
                    )
                    primary = False

            if 'sshPublicKey' in record:
                for sshPublicKey in record.sshPublicKey:
                    resource.setdefault('x509Certificates', []).append(
                        {
                            "value": sshPublicKey
                        }
                    )

        if self.resource_type == self.GROUPS:
            if 'member' in record:
                for dn in record.member:
                    member = self.read_resource(dn)
                    resource.setdefault('members', []).append(
                        {
                            "value": member['id'],
                            "display": member['displayName'],
                            "$ref": f"/Users/{member['id']}"
                        }
                    )

        logger.debug(resource)

        return resource

    def write_resource(self, id: str, resource: Any) -> None:
        dn = f"cn={id},{self.resource_dn}"

        logger.debug(f"[write_resource]: {id} --> {dn}")

        reader = Reader(self.session, self.document_def, dn)
        reader.search()
        writer = Writer.from_cursor(reader)

        if len(writer) == 0:
            record = writer.new(dn)
        else:
            record = writer[0]

        record.cn = id

        if self.resource_type == self.USERS:
            record.uid = resource.pop('userName')
            record.displayName = resource.pop('displayName')

            emails = resource.pop('emails', [])
            if len(emails) > 0:
                record.email = [email['value'] for email in emails]

            pubkeys = resource.pop('x509Certificates', [])
            if len(pubkeys) > 0:
                record.sshPublicKey = [
                    pubkey.get('value') for pubkey in pubkeys
                ]

        if self.resource_type == self.GROUPS:
            record.displayName = resource.pop('displayName')

            members = resource.pop('members', [])

            if len(members):
                record.member = [
                    self.lookup(self.user_dn(), m['value']) for m in members
                ]

        record.info = json.dumps(resource)

        logger.debug(record)
        writer.commit()

    def lookup(self, base: str, id: str) -> str:
        logger.debug(f"[lookup]: {self.description}, id={id}")

        result = self.search(
            base,
            filter=f"(cn={id})",
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
            logger.error(f"Resource with id={id} not found")
            return None

        try:
            resource = self.read_resource(dn)
            return resource
        except Exception as e:
            logger.error(f"Error reading resource {dn}: {e}")
            return None 

    def __setitem__(self, id: str, details: Any) -> None:
        logger.debug(
            f"[__setitem__]: {self.description}, id:{id}, details: {details}"
        )

        resource = json.loads(details)

        self.write_resource(id, resource)
