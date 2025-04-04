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
            "age": 30
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
        filter_obj = Filter('age gt 20')
        assert filter_obj.match(self.user) is True

        # Greater than or equal
        filter_obj = Filter('age ge 30')
        assert filter_obj.match(self.user) is True

        # Less than
        filter_obj = Filter('age lt 40')
        assert filter_obj.match(self.user) is True

        # Less than or equal
        filter_obj = Filter('age le 30')
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
        assert filter_obj.match(self.user) is False

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
            "displayName": "Engineering",
            "members": [
                {
                    "value": "2819c223-7f76-453a-919d-413861904646",
                    "display": "Barbara Jensen",
                    "$ref": "https://example.com/v2/Users/2819c223-7f76"
                },
                {
                    "value": "902c246b-6245-4190-8e05-00816be7344a",
                    "display": "John Smith",
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
            'displayName eq "Engineering"'
        )
        assert filter_obj.match(self.group) is True

        filter_obj = Filter(
            'displayName eq "Marketing"'
        )
        assert filter_obj.match(self.group) is False

    def test_group_members_filter(self):
        filter_obj = Filter(
            'members[display eq "Barbara Jensen"]'
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
            'displayName eq "Engineering"'
            ' and members[display co "Jensen"]')
        assert filter_obj.match(self.group) is True

        filter_obj = Filter(
            'displayName eq "Engineering"'
            ' and not (members[display co "Unknown"])'
        )
        assert filter_obj.match(self.group) is True

        filter_obj = Filter(
            '(displayName co "gin" or meta.resourceType eq "Group")'
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

    def test_member_combined_filters(self):
        filter_obj = Filter(
            'members[display sw "Barbara" and $ref co "2819c223"]'
        )
        assert filter_obj.match(self.group) is True

        filter_obj = Filter(
            'members[display sw "John" and display ew "Smith"]'
        )
        assert filter_obj.match(self.group) is True
