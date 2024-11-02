import json

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from requests import Response
from unittest.mock import patch, Mock, call
from core.tests.util import suppress_errors, suppress_infos

from mailcow_integration.api.client import MailcowAPIClient, RequestType
from mailcow_integration.api.exceptions import *
from mailcow_integration.api.interface.alias import MailcowAlias
from mailcow_integration.api.interface.rspamd import RspamdSettings
from mailcow_integration.squire_mailcow import SquireMailcowManager, get_mailcow_manager
from mailcow_integration.tests.api.test_interfaces import get_alias_json, get_mailbox_json, get_rspamd_json

##################################################################################
# Test cases for the mailcow client
# @since 19 JAN 2023
##################################################################################


class MailcowClientTest(TestCase):
    """Tests the Mailcow API Client"""

    fixtures = []

    def setUp(self):
        self.mailcow_client = MailcowAPIClient(host="example.com", api_key="fake_key")

    def _patch_mailcow_response(self, content: str, status_code=200):
        """Creates a fake response with some content"""
        res = Response()
        res.status_code = status_code
        res._content = bytes(content, "utf-8")
        return res

    def _get_success_response(self, msg="xxx_modified", obj="foo@example.com") -> dict:
        """Gets success json as returned by the Mailcow API"""
        return {"type": "success", "log": [], "msg": [msg, obj]}

    @suppress_infos(logger_name="mailcow_integration")
    @patch("mailcow_integration.api.client.MailcowAPIClient._verify_response_content")
    def test_request(self, mock_verification: Mock):
        """Tests if requests are made with the correct parameters"""
        # Dictionary response
        with patch(
            "requests.request", return_value=self._patch_mailcow_response(json.dumps({"k": "v"}))
        ) as mock_request:
            self.mailcow_client._make_request(
                "my_url", RequestType.GET, params={"foo": "bar"}, data={"hello": "there"}
            )
            # Only a single request is made
            mock_request.assert_called_once()
            # Verification should be called on dict
            mock_verification.assert_called_once_with({"k": "v"}, "example.com/api/v1/my_url")

            # Basic data
            self.assertEqual(len(mock_request.call_args.args), 2)
            self.assertEqual(mock_request.call_args.args[0], RequestType.GET.value)
            self.assertEqual(mock_request.call_args.args[1], "example.com/api/v1/my_url")
            kwargs: dict = mock_request.call_args.kwargs
            self.assertEqual(kwargs.get("params", None), {"foo": "bar"})
            self.assertEqual(kwargs.get("data", None), {"hello": "there"})

            # Headers should be set
            self.assertIn("headers", kwargs)
            headers: dict = kwargs["headers"]
            self.assertEqual(headers.get("Content-Type", None), "application/json")
            self.assertEqual(headers.get("X-API-Key", None), "fake_key")
            self.assertEqual(headers.get("user-agent", None), "squire/1.0.0")

        mock_verification.reset_mock()

        # List response
        with patch(
            "requests.request", return_value=self._patch_mailcow_response(json.dumps([{"a": 1}, {"b": 2}, {"c": 3}]))
        ) as mock_request:
            self.mailcow_client._make_request(
                "my_url", RequestType.GET, params={"foo": "bar"}, data={"hello": "there"}
            )
            # Only one request is made
            mock_request.assert_called_once()
            # Verification should be called on dict
            mock_verification.assert_has_calls(
                [
                    call({"a": 1}, "example.com/api/v1/my_url"),
                    call({"b": 2}, "example.com/api/v1/my_url"),
                    call({"c": 3}, "example.com/api/v1/my_url"),
                ]
            )

        # Exception response (cannot JSON decode)
        with patch("requests.request", return_value=self._patch_mailcow_response("foo")) as mock_request:
            with self.assertRaisesMessage(MailcowException, "Unexpected response"):
                self.mailcow_client._make_request(
                    "my_url", RequestType.GET, params={"foo": "bar"}, data={"hello": "there"}
                )

    @suppress_errors(logger_name="mailcow_integration.api.client")
    def test_response_verification(self):
        """Tests if responses given by the API are verified properly"""
        # Empty response
        with self.assertRaisesMessage(MailcowException, "empty response"):
            self.mailcow_client._verify_response_content({}, "my_url")

        # Incorrect API key
        with self.assertRaisesMessage(MailcowAuthException, "authentication failed"):
            self.mailcow_client._verify_response_content({"type": "error", "msg": "authentication failed"}, "my_url")

        # No write access (only read access)
        with self.assertRaisesMessage(MailcowAPIReadWriteAccessDenied, "API read/write access denied"):
            self.mailcow_client._verify_response_content(
                {"type": "error", "msg": "API read/write access denied"}, "my_url"
            )

        # No API access (not whitelisted)
        with self.assertRaisesMessage(MailcowAPIAccessDenied, "api access denied"):
            self.mailcow_client._verify_response_content({"type": "error", "msg": "api access denied"}, "my_url")

        # Invalid API route
        with self.assertRaisesMessage(MailcowRouteNotFoundException, "route not found"):
            self.mailcow_client._verify_response_content({"type": "error", "msg": "route not found"}, "my_url")

        # Other exception for "error" response
        with self.assertRaisesMessage(MailcowException, "keep off the grass"):
            self.mailcow_client._verify_response_content({"type": "error", "msg": "keep off the grass"}, "my_url")

        # Invalid POST parameters
        with self.assertRaisesMessage(MailcowException, "look before you cross the road"):
            self.mailcow_client._verify_response_content(
                {"type": "danger", "msg": "look before you cross the road"}, "my_url"
            )

        # No invalid data passed
        try:
            self.mailcow_client._verify_response_content(
                {"type": "success", "msg": "Your request was handled successfully. Woohoo!"}, "my_url"
            )
        except MailcowException as e:
            self.fail(f"Exception should not be raised: {e}")

    ################
    # ALIASES
    ################
    @patch(
        "mailcow_integration.api.client.MailcowAPIClient._make_request",
        return_value=[
            {**get_alias_json(), "address": "foo@example.com"},
            {**get_alias_json(), "address": "bar@example.com"},
        ],
    )
    def test_get_alias_all(self, mock_request: Mock):
        """Tests fetching all aliases"""
        res = list(self.mailcow_client.get_alias_all())

        # JSON is converted to aliases
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].address, "foo@example.com")
        self.assertEqual(res[1].address, "bar@example.com")

        # Correct route is used
        mock_request.assert_called_once_with("get/alias/all")

    @patch(
        "mailcow_integration.api.client.MailcowAPIClient._make_request",
        return_value={**get_alias_json(), "address": "foo@example.com"},
    )
    def test_get_alias_id(self, mock_request: Mock):
        """Tests fetching a specific alias"""
        res = self.mailcow_client.get_alias(999)

        # JSON is converted to alias
        self.assertEqual(res.address, "foo@example.com")

        # Correct route is used
        mock_request.assert_called_once_with("get/alias/999")

    def test_update_alias(self):
        """Tests updating a specific alias"""
        alias = MailcowAlias("foo@example.com", [], 999, active=True, sogo_visible=False, public_comment="comment")

        # goto-addresses
        alias.goto = ["bar@example.com", "baz@example.com"]
        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("alias_modified", "foo@example.com"),
        ) as mock_request:
            self.mailcow_client.update_alias(alias)

            # Correct endpoint
            self.assertEqual(len(mock_request.call_args.args), 1)
            self.assertEqual(mock_request.call_args.args[0], "edit/alias/999")

            # data is JSON-encoded
            kwargs: dict = mock_request.call_args.kwargs
            data = kwargs.get("data", None)
            self.assertIsInstance(data, str)
            self.assertDictEqual(
                json.loads(data),
                {
                    "items": [999],
                    "attr": {
                        "address": "foo@example.com",
                        "active": 1,
                        "public_comment": "comment",
                        "private_comment": "",
                        "sogo_visible": 0,
                        "goto": "bar@example.com,baz@example.com",
                    },
                },
            )

        # ham
        alias.goto = ["ham@localhost"]
        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("alias_modified", "foo@example.com"),
        ) as mock_request:
            self.mailcow_client.update_alias(alias)

            # data is JSON-encoded
            kwargs: dict = mock_request.call_args.kwargs
            data = kwargs.get("data", None)
            self.assertIsInstance(data, str)
            self.assertDictEqual(
                json.loads(data),
                {
                    "items": [999],
                    "attr": {
                        "address": "foo@example.com",
                        "active": 1,
                        "public_comment": "comment",
                        "private_comment": "",
                        "sogo_visible": 0,
                        "goto_ham": 1,
                    },
                },
            )

        # spam
        alias.goto = ["spam@localhost"]
        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("alias_modified", "foo@example.com"),
        ) as mock_request:
            self.mailcow_client.update_alias(alias)

            # spam attr present, goto missing (assumes correct structure is verified earlier in this test)
            attr: dict = json.loads(mock_request.call_args.kwargs["data"])["attr"]
            self.assertEqual(attr.get("goto_spam", None), 1)
            self.assertNotIn("goto", attr)
            self.assertNotIn("goto_ham", attr)
            self.assertNotIn("goto_null", attr)

        # silent discard
        alias.goto = ["null@localhost"]
        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("alias_modified", "foo@example.com"),
        ) as mock_request:
            self.mailcow_client.update_alias(alias)

            # null attr present, goto missing (assumes correct structure is verified earlier in this test)
            attr: dict = json.loads(mock_request.call_args.kwargs["data"])["attr"]
            self.assertEqual(attr.get("goto_null", None), 1)
            self.assertNotIn("goto", attr)
            self.assertNotIn("goto_ham", attr)
            self.assertNotIn("goto_spam", attr)

    def test_add_alias(self):
        """Tests creating a specific alias"""
        alias = MailcowAlias("foo@example.com", [], active=True, sogo_visible=False, public_comment="comment")

        # goto-addresses
        alias.goto = ["bar@example.com", "baz@example.com"]
        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("alias_created", "foo@example.com"),
        ) as mock_request:
            self.mailcow_client.create_alias(alias)

            # Correct endpoint
            self.assertEqual(len(mock_request.call_args.args), 1)
            self.assertEqual(mock_request.call_args.args[0], "add/alias")

            # data is JSON-encoded
            kwargs: dict = mock_request.call_args.kwargs
            data = kwargs.get("data", None)
            self.assertIsInstance(data, str)
            self.assertDictEqual(
                json.loads(data),
                {
                    "address": "foo@example.com",
                    "active": 1,
                    "public_comment": "comment",
                    "private_comment": "",
                    "sogo_visible": 0,
                    "goto": "bar@example.com,baz@example.com",
                },
            )

        # ham
        alias.goto = ["ham@localhost"]
        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("alias_created", "foo@example.com"),
        ) as mock_request:
            self.mailcow_client.create_alias(alias)

            # data is JSON-encoded
            kwargs: dict = mock_request.call_args.kwargs
            data = kwargs.get("data", None)
            self.assertIsInstance(data, str)
            self.assertDictEqual(
                json.loads(data),
                {
                    "address": "foo@example.com",
                    "active": 1,
                    "public_comment": "comment",
                    "private_comment": "",
                    "sogo_visible": 0,
                    "goto_ham": 1,
                },
            )

        # spam
        alias.goto = ["spam@localhost"]
        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("alias_created", "foo@example.com"),
        ) as mock_request:
            self.mailcow_client.create_alias(alias)

            # spam attr present, goto missing (assumes correct structure is verified earlier in this test)
            attr: dict = json.loads(mock_request.call_args.kwargs["data"])
            self.assertEqual(attr.get("goto_spam", None), 1)
            self.assertNotIn("goto", attr)
            self.assertNotIn("goto_ham", attr)
            self.assertNotIn("goto_null", attr)

        # silent discard
        alias.goto = ["null@localhost"]
        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("alias_created", "foo@example.com"),
        ) as mock_request:
            self.mailcow_client.create_alias(alias)

            # null attr present, goto missing (assumes correct structure is verified earlier in this test)
            attr: dict = json.loads(mock_request.call_args.kwargs["data"])
            self.assertEqual(attr.get("goto_null", None), 1)
            self.assertNotIn("goto", attr)
            self.assertNotIn("goto_ham", attr)
            self.assertNotIn("goto_spam", attr)

    def test_delete_aliases(self):
        """Tests deleting a specific alias"""
        aliases = [
            MailcowAlias("foo@example.com", ["bar@example.com", "baz@example.com"], 999),
            MailcowAlias("oof@example.com", ["rab@example.com", "zab@example.com"], 998),
        ]

        # goto-addresses
        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("alias_removed", "foo@example.com, oof@example.com"),
        ) as mock_request:
            self.mailcow_client.delete_aliases(aliases)

            # Correct endpoint
            self.assertEqual(len(mock_request.call_args.args), 1)
            self.assertEqual(mock_request.call_args.args[0], "delete/alias")

            # data is JSON-encoded
            kwargs: dict = mock_request.call_args.kwargs
            data = kwargs.get("data", None)
            self.assertIsInstance(data, str)
            self.assertListEqual(json.loads(data), [str(999), str(998)])

    ################
    # MAILBOXES
    ################
    @patch(
        "mailcow_integration.api.client.MailcowAPIClient._make_request",
        return_value=[
            {**get_mailbox_json(), "username": "foo@example.com"},
            {**get_mailbox_json(), "username": "bar@example.com"},
        ],
    )
    def test_get_mailbox_all(self, mock_request: Mock):
        """Tests fetching all mailboxes"""
        res = list(self.mailcow_client.get_mailbox_all())

        # JSON is converted to mailboxes
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].username, "foo@example.com")
        self.assertEqual(res[1].username, "bar@example.com")

        # Correct route is used
        mock_request.assert_called_once_with("get/mailbox/all")

    ################
    # RSPAMD SETTINGS
    ################
    @patch(
        "mailcow_integration.api.client.MailcowAPIClient._make_request",
        return_value=[{**get_rspamd_json(), "id": 999}, {**get_rspamd_json(), "id": 1234}],
    )
    def test_get_rspamd_all(self, mock_request: Mock):
        """Tests fetching all rspamd settings"""
        res = self.mailcow_client.get_rspamd_setting_all()
        res = list(res)

        # JSON is converted to rspamd settings
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].id, 999)
        self.assertEqual(res[1].id, 1234)

        # Correct route is used
        mock_request.assert_called_once_with("get/rsetting/all")

    @patch(
        "mailcow_integration.api.client.MailcowAPIClient._make_request",
        return_value={**get_rspamd_json(), "id": 999, "desc": "COOL RULE"},
    )
    def test_get_rspamd_id(self, mock_request: Mock):
        """Tests fetching a specific rspamd setting"""
        res = self.mailcow_client.get_rspamd_setting(999)

        # JSON is converted to alias
        self.assertEqual(res.desc, "COOL RULE")

        # Correct route is used
        mock_request.assert_called_once_with("get/rsetting/999")

    def test_update_rspamd(self):
        """Tests updating an rspamd setting"""
        rsetting = RspamdSettings(999, "description", "RULE", active=True)

        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("rsetting_modified", "999"),
        ) as mock_request:
            self.mailcow_client.update_rspamd_setting(rsetting)

            # Correct endpoint
            self.assertEqual(len(mock_request.call_args.args), 1)
            self.assertEqual(mock_request.call_args.args[0], "edit/rsetting")

            # data is JSON-encoded
            kwargs: dict = mock_request.call_args.kwargs
            data = kwargs.get("data", None)
            self.assertIsInstance(data, str)
            self.assertDictEqual(
                json.loads(data),
                {
                    "items": [999],
                    "attr": {
                        "active": 1,
                        "desc": "description",
                        "content": "RULE",
                    },
                },
            )

    def test_add_rspamd(self):
        """Tests creating an rspamd setting"""
        rsetting = RspamdSettings(None, "description", "RULE", active=False)

        with patch(
            "mailcow_integration.api.client.MailcowAPIClient._make_request",
            return_value=self._get_success_response("rsetting_created", "999"),
        ) as mock_request:
            self.mailcow_client.create_rspamd_setting(rsetting)

            # Correct endpoint
            self.assertEqual(len(mock_request.call_args.args), 1)
            self.assertEqual(mock_request.call_args.args[0], "add/rsetting")

            # data is JSON-encoded
            kwargs: dict = mock_request.call_args.kwargs
            data = kwargs.get("data", None)
            self.assertIsInstance(data, str)
            self.assertDictEqual(
                json.loads(data),
                {
                    "desc": "description",
                    "content": "RULE",
                    "active": 0,
                },
            )
