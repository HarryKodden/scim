import json
import pytest

from filter import Filter


class TestFilter:
    def setup_method(self):
        # Test resources
        self.basic_user = {
            "userName": "bjensen",
            "name": {
                "familyName": "Jensen",
                "givenName": "Barbara"
            },
            "emails": [
                {
                    "value": "bjensen@example.com",
                    "type": "work",
                    "primary": True
                },
                {
                    "value": "babs@jensen.org",
                    "type": "home"
                }
            ],
            "active": True,
            "meta": {
                "resourceType": "User",
                "created": "2010-01-23T04:56:22Z",
                "lastModified": "2011-05-13T04:42:34Z"
            },
            "age": 3
        }

        class ResourceMock:
            def __init__(self, data):
                self.data = data

            def model_dump_json(self, by_alias=True, exclude_none=True):
                return json.dumps(self.data)

        self.user = ResourceMock(self.basic_user)

    def test_empty_filter(self):
        filter_obj = Filter("")
        assert filter_obj.match(self.user) is True

        filter_obj = Filter(None)
        assert filter_obj.match(self.user) is True

    def test_equality_filter(self):
        filter_obj = Filter('userName eq "bjensen"')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('userName eq "wrong"')
        assert filter_obj.match(self.user) is False

    def test_sub_attribute_filter(self):
        filter_obj = Filter('name.familyName eq "Jensen"')
        assert filter_obj.match(self.user) is True

    def test_list_attribute_filter(self):
        filter_obj = Filter('emails[type eq "work"]')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('emails[value co "jensen.org"]')
        assert filter_obj.match(self.user) is True

    def test_string_operators(self):
        # Contains
        filter_obj = Filter('userName co "jens"')
        assert filter_obj.match(self.user) is True

        # Starts with
        filter_obj = Filter('userName sw "b"')
        assert filter_obj.match(self.user) is True

        # Ends with
        filter_obj = Filter('userName ew "sen"')
        assert filter_obj.match(self.user) is True

    def test_present_operator(self):
        filter_obj = Filter('userName pr')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('nonexistent pr')
        assert filter_obj.match(self.user) is False

    def test_numeric_operators(self):
        # Greater than
        filter_obj = Filter('age gt 2')
        assert filter_obj.match(self.user) is True

        # Greater than or equal
        filter_obj = Filter('age ge 3')
        assert filter_obj.match(self.user) is True

        # Less than
        filter_obj = Filter('age lt 4')
        assert filter_obj.match(self.user) is True

        # Less than or equal
        filter_obj = Filter('age le 3')
        assert filter_obj.match(self.user) is True

    def test_logical_operators(self):
        # AND
        filter_obj = Filter('userName eq "bjensen" and active eq true')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('userName eq "bjensen" and active eq false')
        assert filter_obj.match(self.user) is False

        # OR
        filter_obj = Filter('userName eq "wrong" or active eq true')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('userName eq "wrong" or active eq false')
        assert filter_obj.match(self.user) is False

    def test_negation(self):
        filter_obj = Filter('not (userName eq "wrong")')
        assert filter_obj.match(self.user) is True

    def test_complex_filters(self):
        # Complex AND+OR
        filter_obj = Filter(
            '(userName eq "bjensen" or name.givenName eq "Barbara")'
            ' and active eq true'
        )
        assert filter_obj.match(self.user) is True

        # Complex with list items
        filter_obj = Filter('emails[type eq "work" and value co "example"]')
        assert filter_obj.match(self.user) is True

    def test_invalid_filter(self):
        with pytest.raises(Exception) as excinfo:
            Filter('invalid filter syntax')
        assert "Filter is not valid" in str(excinfo.value)

    def test_non_existent_attributes(self):
        filter_obj = Filter('nonExistentAttr eq "value"')
        assert filter_obj.match(self.user) is False


class TestUserFilter:
    def setup_method(self):
        # Sample user data
        self.basic_user = {
            "id": "2819c223-7f76-453a-919d-413861904646",
            "userName": "bjensen",
            "name": {
                "familyName": "Jensen",
                "givenName": "Barbara"
            },
            "emails": [
                {
                    "value": "bjensen@example.com",
                    "type": "work",
                    "primary": True
                },
                {
                    "value": "babs@jensen.org",
                    "type": "home"
                }
            ],
            "active": True,
            "meta": {
                "resourceType": "User",
                "created": "2010-01-23T04:56:22Z",
                "lastModified": "2011-05-13T04:42:34Z",
                "version": "W/\"3694e05e9dff591\""
            },
            "phoneNumbers": [
                {"value": "555-555-5555", "type": "work"}
            ],
            "addresses": [
                {
                    "streetAddress": "123 Main St",
                    "locality": "Anytown",
                    "region": "CA",
                    "postalCode": "12345",
                    "country": "USA",
                    "type": "work"
                }
            ],
            "age": 30
        }

        class ResourceMock:
            def __init__(self, data):
                self.data = data

            def model_dump_json(self, by_alias=True, exclude_none=True):
                return json.dumps(self.data)

        self.user = ResourceMock(self.basic_user)

    def test_basic_user_filter(self):
        filter_obj = Filter('userName eq "bjensen"')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('userName eq "wrong"')
        assert filter_obj.match(self.user) is False

    def test_user_name_components_filter(self):
        filter_obj = Filter('name.familyName eq "Jensen"')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('name.givenName eq "Barbara"')
        assert filter_obj.match(self.user) is True

    def test_user_email_filter(self):
        filter_obj = Filter('emails[type eq "work"]')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('emails[value co "jensen.org"]')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter(
            'emails[value co "example.com"'
            ' and primary eq true]'
        )
        assert filter_obj.match(self.user) is True

    def test_user_meta_filter(self):
        filter_obj = Filter('meta.resourceType eq "User"')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('meta.created le "2020-01-01T00:00:00Z"')
        assert filter_obj.match(self.user) is True

    def test_user_id_filter(self):
        filter_obj = Filter('id eq "2819c223-7f76-453a-919d-413861904646"')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('id sw "2819"')
        assert filter_obj.match(self.user) is True

    def test_user_address_filter(self):
        filter_obj = Filter('addresses[country eq "USA"]')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter(
            'addresses[postalCode sw "123"'
            ' and region eq "CA"]'
        )
        assert filter_obj.match(self.user) is True

    def test_user_phone_filter(self):
        filter_obj = Filter(
            'phoneNumbers[value eq "555-555-5555"]'
        )
        assert filter_obj.match(self.user) is True

    def test_user_active_filter(self):
        filter_obj = Filter('active eq true')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('active eq false')
        assert filter_obj.match(self.user) is False

    def test_complex_user_filters(self):
        filter_obj = Filter(
            'userName eq "bjensen"'
            ' and emails[type eq "work"]'
        )
        assert filter_obj.match(self.user) is True

        filter_obj = Filter(
            'name.familyName eq "Jensen"'
            ' and addresses[country eq "USA"]'
        )
        assert filter_obj.match(self.user) is True

        filter_obj = Filter(
            '(emails[type eq "work"]'
            ' or emails[type eq "home"]) and active eq true'
        )
        assert filter_obj.match(self.user) is True

        filter_obj = Filter(
            'userName sw "b"'
            ' and not (name.givenName eq "John")'
        )
        assert filter_obj.match(self.user) is True

    def test_user_attribute_presence(self):
        filter_obj = Filter('userName pr')
        assert filter_obj.match(self.user) is True

        filter_obj = Filter('nonexistentField pr')
        assert filter_obj.match(self.user) is False

        filter_obj = Filter('emails pr and phoneNumbers pr')
        assert filter_obj.match(self.user) is True


class TestGroupFilter:
    def setup_method(self):
        # Sample group data
        self.basic_group = {
            "id": "e9e30dba-f08f-4109-8486-d5c6a331660a",
            "displayName": "Example Group",
            "members": [
                {
                    "value": "2819c223-7f76-453a-919d-413861904646",
                    "display": "User One",
                    "$ref": "https://example.com/v2/Users/2819c223-7f76"
                },
                {
                    "value": "902c246b-6245-4190-8e05-00816be7344a",
                    "display": "User Two",
                    "$ref": "https://example.com/v2/Users/902c246b-6245"
                }
            ],
            "meta": {
                "resourceType": "Group",
                "created": "2010-01-23T04:56:22Z",
                "lastModified": "2011-05-13T04:42:34Z",
                "version": "W/\"3694e05e9dff591\""
            }
        }

        class ResourceMock:
            def __init__(self, data):
                self.data = data

            def model_dump_json(self, by_alias=True, exclude_none=True):
                return json.dumps(self.data)

        self.group = ResourceMock(self.basic_group)

    def test_basic_group_filter(self):
        filter_obj = Filter(
            'displayName eq "Example Group"'
        )
        assert filter_obj.match(self.group) is True

        filter_obj = Filter(
            'displayName eq "Other Group"'
        )
        assert filter_obj.match(self.group) is False

    def test_group_members_filter(self):
        filter_obj = Filter(
            'members[display eq "User One"]'
        )
        assert filter_obj.match(self.group) is True

        filter_obj = Filter('members[display eq "Jane Doe"]')
        assert filter_obj.match(self.group) is False

    def test_member_reference_filter(self):
        filter_obj = Filter('members[$ref co "2819c223"]')
        assert filter_obj.match(self.group) is True

    def test_group_meta_filter(self):
        filter_obj = Filter(
            'meta.resourceType eq "Group"'
        )
        assert filter_obj.match(self.group) is True

        filter_obj = Filter(
            'meta.created le "2020-01-01T00:00:00Z"'
        )
        assert filter_obj.match(self.group) is True

    def test_group_member_count(self):
        filter_obj = Filter('members pr')
        assert filter_obj.match(self.group) is True

    def test_complex_group_filters(self):
        filter_obj = Filter(
            'displayName eq "Example Group"'
            ' and members[display co "User"]')
        assert filter_obj.match(self.group) is True

        filter_obj = Filter(
            'displayName eq "Example Group"'
            ' and not (members[display co "Unknown"])'
        )
        assert filter_obj.match(self.group) is True

        filter_obj = Filter(
            '(displayName co "Exam" or meta.resourceType eq "Group")'
            ' and members pr'
        )
        assert filter_obj.match(self.group) is True

    def test_group_id_filter(self):
        filter_obj = Filter(
            'id eq "e9e30dba-f08f-4109-8486-d5c6a331660a"'
        )
        assert filter_obj.match(self.group) is True

        filter_obj = Filter('id sw "e9e30"')
        assert filter_obj.match(self.group) is True

    def test_group_urn_key_no_split(self):
        # Regression test: ensure URN keys containing ':' are treated as
        # a single top-level key (not split on ':') when resolving paths.
        sample_group = {
            "urn:mace:surf.nl:sram:scim:extension:Group": {
                "urn": "surf_demo:test30"
            }
        }

        class ResourceMockLocal:
            def __init__(self, data):
                self.data = data

            def model_dump_json(self, by_alias=True, exclude_none=True):
                return json.dumps(self.data)

        resource = ResourceMockLocal(sample_group)

        filter_obj = Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn co "surf_demo:test30"')
        assert filter_obj.match(resource) is True

    def test_group_extension_links_name_equals_logo(self):
        # Ensure we can filter on 'links' array sub-attribute 'name' == 'logo'
        sample_group = {
            "urn:mace:surf.nl:sram:scim:extension:Group": {
                "links": [
                    {"value": "https://example.org/1", "name": "sbs_url"},
                    {"value": "https://example.org/2", "name": "logo"}
                ]
            }
        }

        class ResourceMockLocal:
            def __init__(self, data):
                self.data = data

            def model_dump_json(self, by_alias=True, exclude_none=True):
                return json.dumps(self.data)

        resource = ResourceMockLocal(sample_group)

        # Use bracketed sub-filter to check list items' sub-attributes
        filter_obj = Filter('urn:mace:surf.nl:sram:scim:extension:Group.links[name eq "logo"]')
        assert filter_obj.match(resource) is True

    def test_group_extension_operator_variants(self):
        # Verify different string operators against the nested extension urn
        sample_group = {
            "urn:mace:surf.nl:sram:scim:extension:Group": {
                "urn": "surf_demo:test30"
            }
        }

        class ResourceMockLocal:
            def __init__(self, data):
                self.data = data

            def model_dump_json(self, by_alias=True, exclude_none=True):
                return json.dumps(self.data)

        resource = ResourceMockLocal(sample_group)

        # contains
        assert Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn co "test30"').match(resource) is True
        # starts with
        assert Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn sw "surf_demo"').match(resource) is True
        # ends with
        assert Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn ew "test30"').match(resource) is True
        # equals
        assert Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn eq "surf_demo:test30"').match(resource) is True
        # not equals
        assert Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn ne "other"').match(resource) is True

    def test_group_extension_nested_filter(self):
        # Sample group resource with nested extension attribute
        sample_group = {
            "id": "404c8c31-e710-4214-90c1-418a39daccef",
            "meta": {
                "location": "/Groups/404c8c31-e710-4214-90c1-418a39daccef",
                "resourceType": "Group",
                "lastModified": "2026-02-19T13:17:43.717981"
            },
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:Group",
                "urn:mace:surf.nl:sram:scim:extension:Group"
            ],
            "urn:mace:surf.nl:sram:scim:extension:Group": {
                "description": "Sample group with extension attributes",
                "urn": "example:test30",
                "links": [
                    {"value": "https://example.com/593c0208-723f-4a69-8b75-843fad34d6a0", "name": "sbs_url"},
                    {"value": "https://example.com/cd4935f2-9d99-4bf4-b5b3-b75dfd1d8c23", "name": "logo"}
                ]
            },
            "displayName": "Example - test30",
            "externalId": "593c0208-723f-4a69-8b75-843fad34d6a0",
            "members": [
                {
                    "value": "eb572ad0-5847-4071-adfb-3b8dd6adeb6f",
                    "display": "Harry Kodden",
                    "$ref": "/Users/eb572ad0-5847-4071-adfb-3b8dd6adeb6f"
                }
            ]
        }

        class ResourceMockLocal:
            def __init__(self, data):
                self.data = data

            def model_dump_json(self, by_alias=True, exclude_none=True):
                return json.dumps(self.data)

        resource = ResourceMockLocal(sample_group)

        # Filter targeting the nested extension urn field
        filter_obj = Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn co "example:test30"')
        assert filter_obj.match(resource) is True

        filter_obj = Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn sw "example"')
        assert filter_obj.match(resource) is True

        filter_obj = Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn co "test30"')
        assert filter_obj.match(resource) is True

        filter_obj = Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn co "test32"')
        assert filter_obj.match(resource) is False

        filter_obj = Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn ew "test30"')
        assert filter_obj.match(resource) is True

        filter_obj = Filter('urn:mace:surf.nl:sram:scim:extension:Group.urn ew "test32"')
        assert filter_obj.match(resource) is False

        filter_obj = Filter('urn:mace:surf.nl:sram:scim:extension:Group.links.logo ew "test32"')
        assert filter_obj.match(resource) is False

    def test_member_combined_filters(self):
        filter_obj = Filter(
            'members[display sw "User" and $ref co "2819c223"]'
        )
        assert filter_obj.match(self.group) is True

        filter_obj = Filter(
            'members[display sw "User" and display ew "Two"]'
        )
        assert filter_obj.match(self.group) is True
