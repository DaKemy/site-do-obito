import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

os.environ.setdefault('FLASK_SECRET_KEY', 'test-session-secret')
os.environ.setdefault('ADMIN_USERNAME', 'test-admin')
os.environ.setdefault('ADMIN_PASSWORD', 'test-admin-password')
os.environ.setdefault('CPF_HASH_SECRET', 'test-cpf-hash-secret')

import app as app_module


class AccountFlowTests(unittest.TestCase):
    registration = {
        'name': 'Teste Cliente',
        'whatsapp': '(41) 99999-9999',
        'email': 'cliente@example.com',
        'cpf': '529.982.247-25',
        'password': 'senha-segura-123',
    }

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'test.sqlite'
        self.db_patch = patch.object(app_module, 'DB_PATH', self.db_path)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        app_module.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
        app_module.init_db()
        app_module.seed_prizes()
        self.client = app_module.app.test_client()

    def register_and_verify(self):
        with patch.object(app_module, 'send_account_email') as send_email:
            response = self.client.post('/api/auth/register', json=self.registration)
        self.assertEqual(response.status_code, 202)
        body = send_email.call_args.args[2]
        link = re.search(r'https?://\S+', body).group(0)
        token = parse_qs(urlparse(link).query)['verificar'][0]
        return token

    def test_cpf_checksum(self):
        self.assertTrue(app_module.valid_cpf('529.982.247-25'))
        self.assertFalse(app_module.valid_cpf('111.111.111-11'))
        self.assertFalse(app_module.valid_cpf('529.982.247-24'))

    def test_registration_verification_login_and_spin(self):
        invalid = dict(self.registration, cpf='52998224724')
        response = self.client.post('/api/auth/register', json=invalid)
        self.assertEqual(response.status_code, 400)

        token = self.register_and_verify()
        conn = sqlite3.connect(self.db_path)
        stored = conn.execute(
            'SELECT cpf_hash, password_hash, verification_token_hash FROM customers'
        ).fetchone()
        self.assertNotIn('52998224725', stored[0])
        self.assertNotEqual(stored[1], self.registration['password'])
        self.assertNotEqual(stored[2], token)
        conn.close()

        pending_login = self.client.post('/api/auth/login', json={
            'identifier': self.registration['email'],
            'password': self.registration['password'],
        })
        self.assertEqual(pending_login.status_code, 403)

        verified = self.client.post('/api/auth/verify-email', json={'token': token})
        self.assertEqual(verified.status_code, 200)
        login = self.client.post('/api/auth/login', json={
            'identifier': '52998224725',
            'password': self.registration['password'],
        })
        self.assertEqual(login.status_code, 200)

        customer = self.client.get('/api/auth/me').get_json()['customer']
        self.assertNotIn('cpf', customer)
        self.assertEqual(self.client.get(f'/api/customers/{customer["id"] + 1}').status_code, 403)

        spin = self.client.post('/api/spins/roll', json={})
        self.assertEqual(spin.status_code, 200)
        result = spin.get_json()['result']
        self.assertEqual(result['segmentIndex'], result['prizeId'] - 1)
        self.assertEqual(self.client.post('/api/spins/roll', json={}).status_code, 400)

    def test_duplicate_registration_and_admin_data_minimization(self):
        self.register_and_verify()
        duplicate = dict(self.registration, email='other@example.com', whatsapp='41988887777')
        response = self.client.post('/api/auth/register', json=duplicate)
        self.assertEqual(response.status_code, 409)

        unauthorized = self.client.get('/api/admin/customers')
        self.assertEqual(unauthorized.status_code, 401)
        admin_login = self.client.post('/api/admin/login', json={
            'username': 'test-admin',
            'password': 'test-admin-password',
        })
        self.assertEqual(admin_login.status_code, 200)
        customers = self.client.get('/api/admin/customers').get_json()['customers']
        self.assertEqual(len(customers), 1)
        self.assertNotIn('cpf_hash', customers[0])
        self.assertNotIn('password_hash', customers[0])
        self.assertNotIn('verification_token_hash', customers[0])

    def test_resend_verification_by_cpf(self):
        self.register_and_verify()
        with patch.object(app_module, 'send_account_email') as send_email:
            response = self.client.post('/api/auth/resend-verification', json={
                'identifier': '52998224725',
                'password': self.registration['password'],
            })
        self.assertEqual(response.status_code, 200)
        link = re.search(r'https?://\S+', send_email.call_args.args[2]).group(0)
        token = parse_qs(urlparse(link).query)['verificar'][0]
        self.assertEqual(
            self.client.post('/api/auth/verify-email', json={'token': token}).status_code,
            200,
        )

    def test_password_reset_and_static_routes(self):
        token = self.register_and_verify()
        self.client.post('/api/auth/verify-email', json={'token': token})

        with patch.object(app_module, 'send_account_email') as send_email:
            response = self.client.post('/api/auth/password-reset', json={
                'email': self.registration['email'],
            })
        self.assertEqual(response.status_code, 200)
        body = send_email.call_args.args[2]
        link = re.search(r'https?://\S+', body).group(0)
        reset_token = parse_qs(urlparse(link).query)['token'][0]
        reset = self.client.post('/api/auth/reset-password', json={
            'token': reset_token,
            'password': 'nova-senha-segura',
        })
        self.assertEqual(reset.status_code, 200)

        old_login = self.client.post('/api/auth/login', json={
            'identifier': self.registration['email'],
            'password': self.registration['password'],
        })
        self.assertEqual(old_login.status_code, 401)
        new_login = self.client.post('/api/auth/login', json={
            'identifier': self.registration['email'],
            'password': 'nova-senha-segura',
        })
        self.assertEqual(new_login.status_code, 200)

        for path in ('/', '/mvp', '/esqueci-senha.html'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            response.close()
        self.assertEqual(self.client.get('/mvp-tattoo/data.sqlite').status_code, 404)


if __name__ == '__main__':
    unittest.main()
