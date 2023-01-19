import json

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from requests import Response
from unittest.mock import patch, Mock, call

from mailcow_integration.api.client import MailcowAPIClient, RequestType
from mailcow_integration.api.exceptions import *
from mailcow_integration.squire_mailcow import SquireMailcowManager, get_mailcow_manager

##################################################################################
# Test cases for the mailcow client
# @since 19 JAN 2023
##################################################################################


class MailcowClientTest(TestCase):
    """ Tests the Mailcow API Client """
    fixtures = []

    def setUp(self):
        self.mailcow_client = MailcowAPIClient(host="example.com", api_key="fake_key")

    def _patch_mailcow_response(self, content: str, status_code=200):
        res = Response()
        res.status_code = status_code
        res._content = bytes(content, 'utf-8')
        return [res]

    @patch('mailcow_integration.api.client.MailcowAPIClient._verify_response_content')
    def test_request(self, mock_verification: Mock):
        """ Tests if requests are made with the correct parameters """
        # Dictionary response
        with patch('requests.request', side_effect=self._patch_mailcow_response(json.dumps({}))) as mock_request:
            self.mailcow_client._make_request("my_url", RequestType.GET, params={'foo': 'bar'}, data={'hello': 'there'})
            mock_request.assert_called_once()
            # Verification should be called on dict
            mock_verification.assert_called_once_with({}, 'example.com/api/v1/my_url')

            # Basic data
            self.assertEqual(len(mock_request.call_args.args), 2)
            self.assertEqual(mock_request.call_args.args[0], RequestType.GET.value)
            self.assertEqual(mock_request.call_args.args[1], "example.com/api/v1/my_url")
            kwargs: dict = mock_request.call_args.kwargs
            self.assertEqual(kwargs.get('params', None), {'foo': 'bar'})
            self.assertEqual(kwargs.get('data', None), {'hello': 'there'})

            # Headers should be set
            self.assertIn('headers', kwargs)
            headers: dict = kwargs['headers']
            self.assertEqual(headers.get('Content-Type', None), 'application/json')
            self.assertEqual(headers.get('X-API-Key', None), 'fake_key')
            self.assertEqual(headers.get('user-agent', None), 'squire/1.0.0')

        mock_verification.reset_mock()

        # List response
        with patch('requests.request', side_effect=self._patch_mailcow_response(json.dumps([{'a': 1}, {'b': 2}, {'c': 3}]))) as mock_request:
            self.mailcow_client._make_request("my_url", RequestType.GET, params={'foo': 'bar'}, data={'hello': 'there'})
            mock_request.assert_called_once()
            # Verification should be called on dict
            mock_verification.assert_has_calls([
                call({'a': 1}, 'example.com/api/v1/my_url'),
                call({'b': 2}, 'example.com/api/v1/my_url'),
                call({'c': 3}, 'example.com/api/v1/my_url')
            ])

        # Exception response (cannot JSON decode)
        with patch('requests.request', side_effect=self._patch_mailcow_response('foo')) as mock_request:
            with self.assertRaisesMessage(MailcowException, "Unexpected response"):
                self.mailcow_client._make_request("my_url", RequestType.GET, params={'foo': 'bar'}, data={'hello': 'there'})

    def test_response_verification(self):
        """ Tests if responses given by the API are verified properly """
        # Empty response
        with self.assertRaisesMessage(MailcowException, "empty response"):
            self.mailcow_client._verify_response_content({}, 'my_url')

        # Incorrect API key
        with self.assertRaisesMessage(MailcowAuthException, "authentication failed"):
            self.mailcow_client._verify_response_content({
                "type": "error",
                "msg": "authentication failed"
            }, 'my_url')

        # No write access (only read access)
        with self.assertRaisesMessage(MailcowAPIReadWriteAccessDenied, "API read/write access denied"):
            self.mailcow_client._verify_response_content({
                "type": "error",
                "msg": "API read/write access denied"
            }, 'my_url')

        # No API access (not whitelisted)
        with self.assertRaisesMessage(MailcowAPIAccessDenied, "api access denied"):
            self.mailcow_client._verify_response_content({
                "type": "error",
                "msg": "api access denied"
            }, 'my_url')

        # Invalid API route
        with self.assertRaisesMessage(MailcowRouteNotFoundException, "route not found"):
            self.mailcow_client._verify_response_content({
                "type": "error",
                "msg": "route not found"
            }, 'my_url')

        # Other exception for "error" response
        with self.assertRaisesMessage(MailcowException, "keep off the grass"):
            self.mailcow_client._verify_response_content({
                "type": "error",
                "msg": "keep off the grass"
            }, 'my_url')

        # Invalid POST parameters
        with self.assertRaisesMessage(MailcowException, "look before you cross the road"):
            self.mailcow_client._verify_response_content({
                "type": "danger",
                "msg": "look before you cross the road"
            }, 'my_url')

        # No invalid data passed
        try:
            self.mailcow_client._verify_response_content({
                "type": "success",
                "msg": "Your request was handled successfully. Woohoo!"
            }, 'my_url')
        except MailcowException as e:
            self.fail(f"Exception should not be raised: {e}")
