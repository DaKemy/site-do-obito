import base64
import io
import json
import os
import unittest
import urllib.error
from email import policy
from email.parser import BytesParser
from unittest.mock import patch
from urllib.parse import parse_qs

os.environ.setdefault('FLASK_SECRET_KEY', 'test-session-secret')
os.environ.setdefault('CPF_HASH_SECRET', 'test-cpf-hash-secret')

import app as app_module


class MockResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class GmailApiEmailTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            'EMAIL_PROVIDER': 'gmail_api',
            'GMAIL_CLIENT_ID': 'client-id',
            'GMAIL_CLIENT_SECRET': 'client-secret',
            'GMAIL_REFRESH_TOKEN': 'refresh-token',
            'GMAIL_FROM': 'sender@gmail.com',
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @patch('app.urllib.request.urlopen')
    def test_sends_message_through_gmail_api(self, urlopen):
        urlopen.side_effect = [
            MockResponse({'access_token': 'access-token'}),
            MockResponse({'id': 'message-id'}),
        ]

        app_module.send_account_email(
            'cliente@example.com',
            'Confirme seu e-mail',
            'Acesse o link.',
        )

        token_request, gmail_request = [
            call.args[0] for call in urlopen.call_args_list
        ]
        self.assertEqual(token_request.full_url, 'https://oauth2.googleapis.com/token')
        self.assertEqual(parse_qs(token_request.data.decode('ascii')), {
            'client_id': ['client-id'],
            'client_secret': ['client-secret'],
            'refresh_token': ['refresh-token'],
            'grant_type': ['refresh_token'],
        })
        self.assertEqual(
            gmail_request.full_url,
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
        )
        self.assertEqual(
            gmail_request.get_header('Authorization'),
            'Bearer access-token',
        )
        raw_message = json.loads(gmail_request.data)['raw']
        padded_message = raw_message + '=' * (-len(raw_message) % 4)
        message = BytesParser(policy=policy.default).parsebytes(
            base64.urlsafe_b64decode(padded_message)
        )
        self.assertEqual(message['From'], 'sender@gmail.com')
        self.assertEqual(message['To'], 'cliente@example.com')
        self.assertEqual(message['Subject'], 'Confirme seu e-mail')
        self.assertEqual(message.get_content().strip(), 'Acesse o link.')
        self.assertEqual(urlopen.call_count, 2)

    @patch('app.urllib.request.urlopen')
    def test_reports_gmail_api_rejection(self, urlopen):
        urlopen.side_effect = [
            MockResponse({'access_token': 'access-token'}),
            urllib.error.HTTPError(
                'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                403,
                'Forbidden',
                {},
                io.BytesIO(b''),
            ),
        ]

        with self.assertRaisesRegex(RuntimeError, 'Gmail API returned HTTP 403'):
            app_module.send_account_email(
                'cliente@example.com',
                'Confirme seu e-mail',
                'Acesse o link.',
            )

    def test_requires_all_gmail_api_settings(self):
        with patch.dict(os.environ, {'GMAIL_REFRESH_TOKEN': ''}):
            with self.assertRaisesRegex(RuntimeError, 'GMAIL_REFRESH_TOKEN'):
                app_module.send_account_email(
                    'cliente@example.com',
                    'Confirme seu e-mail',
                    'Acesse o link.',
                )


if __name__ == '__main__':
    unittest.main()
