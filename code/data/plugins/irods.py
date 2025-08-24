import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from requests import session

# from routers import resource
from data.plugins import Plugin

try:
    from irods.user import iRODSUser as BaseIRODSUser, iRODSGroup as BaseIRODSGroup
    from irods.session import iRODSSession
    from irods.models import User, Group
    from irods.exception import UserDoesNotExist, UserGroupDoesNotExist
    from irods.meta import iRODSMeta
except ImportError:
    raise ImportError(
        "python-irodsclient is required for iRODS plugin. Install with: pip install python-irodsclient"
    )

logger = logging.getLogger(__name__)


class iRODSUser(BaseIRODSUser):
    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        for key, value in metadata.items():
            if value is not None:
                self.manager.sess.metadata.add(
                    User, self.name, iRODSMeta(key, value)
                )

    def __repr__(self):
        metadata = {meta.name: meta.value for meta in self.metadata.items()}
        return (
            f"iRODSUser(id={self.id}, name={self.name}, "
            f"metadata={metadata}, info={self.info})"
        )


class iRODSGroup(BaseIRODSGroup):
    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        for key, value in metadata.items():
            if value is not None:
                self.manager.sess.metadata.add(
                    User, self.name, iRODSMeta(key, value)
                )

    def __repr__(self):
        metadata = {meta.name: meta.value for meta in self.metadata.items()}
        members = [str(member) for member in self.members]
        return (
            f"iRODSGroup(id={self.id}, name={self.name}, "
            f"metadata={metadata}, members={members})"
        )


class iRODSPlugin(Plugin):
    """
    iRODS plugin for SCIM user and group management.

    Implements the synchronization policy from:
    https://github.com/HarryKodden/irods-ldap-sync/blob/main/doc/policy.ipynb

    Key features:
    - User and group management in iRODS
    - Metadata synchronization
    - Safe deletion with data preservation
    - Special group creation for orphaned data
    """

    def __init__(
        self,
        resource_type: str,
        irods_host: str = None,
        irods_port: int = 1247,
        irods_user: str = None,
        irods_password: str = None,
        irods_zone: str = None,
    ):
        super().__init__()
        self.resource_type = resource_type
        self.description = f'iRODS-{resource_type}'

        # iRODS connection parameters
        self.irods_host = irods_host
        self.irods_port = irods_port
        self.irods_user = irods_user
        self.irods_password = irods_password
        self.irods_zone = irods_zone

        # Metadata prefixes for SCIM attributes
        self.scim_meta_prefix = "SCIM_"
        self.deleted_meta_key = "DELETED"
        self.timestamp_meta_key = "TIMESTAMP"

        logger.info(f"Initializing iRODS plugin for {resource_type}")

        try:
            # Test connection
            with self._get_session():
                logger.info(
                    f"Successfully connected to iRODS at {irods_host}:{irods_port} zone:{irods_zone}"
                )
        except Exception as e:
            logger.error(f"Failed to connect to iRODS: {e}")
            raise

    def id(self, details: dict) -> str:
        logger.debug(f"Generating ID for {self.resource_type} with details: {details}")

        with self._get_session() as sess:
            if self.resource_type == self.USERS:
                user = sess.users.create(details['userName'], 'rodsuser')
                return str(user.id)
            else:
                group = sess.groups.create(details['displayName'])
                return str(group.id)
        return None

    def _get_session(self) -> iRODSSession:
        """Create and return an iRODS session, with retry on connection errors and a real query to verify connection."""
        try:
            return iRODSSession(
                host=self.irods_host,
                port=self.irods_port,
                user=self.irods_user,
                password=self.irods_password,
                zone=self.irods_zone,
            )
        except Exception as e:
            logger.error(f"Failed to create iRODS session: {e}")
            raise

    def _format_timestamp(self) -> str:
        """Format current timestamp for metadata."""
        return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    def _has_data_ownership(self, sess: iRODSSession, username: str) -> bool:
        """Check if a user owns any data objects or collections."""
        try:
            query = sess.query(sess.data_objects.Collection.name).filter(
                sess.data_objects.DataObject.owner_name == username
            )
            if query.first():
                return True

            query = sess.query(sess.collections.Collection.name).filter(
                sess.collections.Collection.owner_name == username
            )
            if query.first():
                return True

            return False
        except Exception as e:
            logger.warning(f"Failed to check data ownership for {username}: {e}")
            return False

    def _create_special_group_for_deleted_entity(
        self, sess: iRODSSession, original_name: str, entity_type: str
    ) -> str:
        """
        Create a special group for orphaned data when a user/group is deleted.
        Returns the special group name.
        """
        special_group_name = str(uuid.uuid4())

        try:
            sess.user_groups.create(special_group_name)
            logger.info(
                f"Created special group {special_group_name} for deleted {entity_type} {original_name}"
            )

            admin_user = sess.users.get(self.irods_user)
            sess.user_groups.get(special_group_name).addmember(admin_user.name)

            special_group = sess.user_groups.get(special_group_name)
            special_group.metadata.add(self.deleted_meta_key, original_name)
            special_group.metadata.add(self.timestamp_meta_key, self._format_timestamp())

            self._transfer_ownership_to_group(sess, original_name, special_group_name)

            return special_group_name

        except Exception as e:
            logger.error(f"Failed to create special group for {original_name}: {e}")
            raise

    def _transfer_ownership_to_group(
        self, sess: iRODSSession, from_user: str, to_group: str
    ) -> None:
        """Transfer all data ownership from a user to a group."""
        try:
            for res in sess.query(
                sess.data_objects.Collection.name,
                sess.data_objects.DataObject.name,
            ).filter(sess.data_objects.DataObject.owner_name == from_user):
                collection_name = res[sess.data_objects.Collection.name]
                object_name = res[sess.data_objects.DataObject.name]
                object_path = f"{collection_name}/{object_name}"

                sess.permissions.set(
                    sess.permissions.own, object_path, to_group, admin=True
                )

            for res in sess.query(sess.collections.Collection.name).filter(
                sess.collections.Collection.owner_name == from_user
            ):
                collection_name = res[sess.collections.Collection.name]
                sess.permissions.set(
                    sess.permissions.own, collection_name, to_group, admin=True
                )

            logger.info(
                f"Transferred ownership from {from_user} to group {to_group}"
            )

        except Exception as e:
            logger.error(
                f"Failed to transfer ownership from {from_user} to {to_group}: {e}"
            )
            raise

    def __iter__(self) -> Any:
        """Iterate over all users or groups in iRODS."""
        logger.debug(f"[__iter__]: {self.description}")
        with self._get_session() as sess:
            try:
                if self.resource_type == self.USERS:
                    for user_obj in [
                        iRODSUser(sess.users, res) for res in sess.query(User)
                    ]:
                        yield str(user_obj.id)
                else:
                    for group_obj in [
                        iRODSGroup(sess.groups, res) for res in sess.query(Group)
                    ]:
                        yield str(group_obj.id)
                sess.cleanup()
            except Exception as e:
                logger.error(f"Failed to iterate over {self.resource_type}: {e}")
                raise

    def __delitem__(self, id: str) -> None:
        """Delete a user or group from iRODS, handling data ownership appropriately."""
        logger.debug(f"[__delitem__]: {self.description}, id={id}")

        with self._get_session() as sess:
            try:
                if self.resource_type == self.USERS:
                    if self._has_data_ownership(sess, id):
                        special_group = self._create_special_group_for_deleted_entity(
                            sess, id, "user"
                        )
                        logger.info(
                            f"Created special group {special_group} for user {id} with data"
                        )

                    sess.users.remove(id)
                    logger.info(f"Deleted user {id}")

                else:
                    try:
                        group = sess.user_groups.get(id)
                        if group.members or self.metadata:
                            special_group = self._create_special_group_for_deleted_entity(
                                sess, id, "group"
                            )
                            logger.info(
                                f"Created special group {special_group} for group {id}"
                            )
                    except UserGroupDoesNotExist:
                        pass

                    sess.user_groups.remove(id)
                    logger.info(f"Deleted group {id}")

            except (UserDoesNotExist, UserGroupDoesNotExist):
                logger.warning(f"{self.resource_type[:-1]} {id} does not exist")
            except Exception as e:
                logger.error(
                    f"Failed to delete {self.resource_type[:-1]} {id}: {e}"
                )
                raise

    def _irods_read_user(self, id: str) -> iRODSUser:
        logger.info(f"Fetching user {id} from iRODS")
        with self._get_session() as sess:
            return iRODSUser(
                sess.users,
                sess.query(User).filter(User.id == id).first()
            )

    def _irods_read_group(self, id: str) -> iRODSGroup:
        logger.info(f"Fetching group {id} from iRODS")
        with self._get_session() as sess:
            return iRODSGroup(
                sess.groups,
                sess.query(Group).filter(Group.id == id).first()
            )

    def __getitem__(self, id: str) -> Any:
        """Get a user or group resource from iRODS."""
        logger.debug(f"[__getitem__]: {self.description}, id={id}")

        try:
            if self.resource_type == self.USERS:
                user = self._irods_read_user(id)
                logger.info(f"Fetched user {id} from iRODS: {str(user)}")

                metadata = {meta.name: meta.value for meta in user.metadata.items()}

                resource = {
                    'id': id,
                    'userName': user.name,
                    'active': True,
                    'emails': [],
                    "meta": {
                        "location": f"/Users/{id}",
                        "resourceType": "User"
                    }
                }

                for key, value in metadata.items():
                    resource[key] = json.loads(value) if isinstance(value, str) else value

                logger.info(f"User resource: {resource}")
                return resource

            else:
                group = self._irods_read_group(id)
                metadata = {meta.name: meta.value for meta in group.metadata.items()}

                resource = {
                    'id': id,
                    'displayName': group.name,
                    'members': [],
                    'meta': {
                        'location': f"/Groups/{id}",
                        'resourceType': "Group"
                    }
                }

                for member in group.members:
                    logger.info(f"Group member found: {str(member)}")
                    resource['members'].append({
                        'value': str(member.id),
                        'display': member.name,
                        '$ref': f"/Users/{member.id}"
                    })

                for key, value in metadata.items():
                    if key not in ['displayName']:
                        resource[key] = json.loads(value) if isinstance(value, str) else value

                return resource

        except (UserDoesNotExist, UserGroupDoesNotExist):
            logger.warning(f"{self.resource_type[:-1]} {id} does not exist")
            return None
        except Exception as e:
            logger.error(f"Failed to get {self.resource_type[:-1]} {id}: {e}")
            return None

    def __setitem__(self, id: str, details: Any) -> None:
        """Create or update a user or group in iRODS."""
        logger.debug(f"[__setitem__]: {self.description}, id:{id}, details: {details}")

        resource = json.loads(details) if isinstance(details, str) else details

        if 'meta' in resource:
            del resource['meta']

        try:
            if self.resource_type == self.USERS:
                user = self._irods_read_user(id)
                logger.debug(f"Updating existing user {id}, old values: {str(user)}")

                metadata = {}
                for key, value in resource.items():
                    if key not in ['id', 'userName']:
                        metadata[key] = json.dumps(value)

                user.set_metadata(metadata)
                logger.info(f"Updated user {id} in iRODS, new values: {str(user)}")

            else:
                group = self._irods_read_group(id)
                logger.info(f"Group {id} found: {str(group)}")

                current_members = {member.name for member in group.members}
                new_members = {member['value'] for member in resource.get('members', [])}

                logger.info(
                    f"Current members: {current_members}, New members: {new_members}"
                )

                for member_id in new_members - current_members:
                    try:
                        member_user = session.users.get(member_id)
                        group.addmember(member_user.name)
                        logger.debug(f"Added {member_id} to group {id}")
                    except UserDoesNotExist:
                        logger.warning(
                            f"Cannot add non-existent user {member_id} to group {id}"
                        )

                for member_id in current_members - new_members:
                    try:
                        group.removemember(member_id)
                        logger.debug(f"Removed {member_id} from group {id}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to remove {member_id} from group {id}: {e}"
                        )

                metadata = {}
                for key, value in resource.items():
                    if key not in ['id', 'displayName']:
                        metadata[key] = json.dumps(value)

                logger.info(f"Updating group {id} with metadata: {metadata}")
                group.set_metadata(metadata)

        except Exception as e:
            logger.error(
                f"Failed to create/update {self.resource_type[:-1]} {id}: {e}"
            )
            raise
