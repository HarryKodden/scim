"""SRAM LDAP layout helpers and plugin.

Writes the ordered SRAM directory tree from SCIM Users/Groups and optionally
derives the flat projection (PLSC decision A).

Activate with::

    LDAP_HOSTNAME=...
    LDAP_BASENAME=dc=<service>,dc=services,...
    LDAP_LAYOUT=sram-ordered
    LDAP_FLAT_DERIVE=true
"""

from data.plugins.sram_ldap.plugin import SRAM_LDAP_Plugin

__all__ = ["SRAM_LDAP_Plugin"]
