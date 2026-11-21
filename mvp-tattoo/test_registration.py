"""Testes de cadastro sem banco de dados ou envio real de e-mail."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('FLASK_SECRET_KEY', 'test-session-secret')
os.environ.setdefault('CPF_HASH_SECRET', 'test-cpf-hash-secret')

import app as app_module


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, prizes=None):
        self.executions = []
        self.committed = False
        self.closed = False
        self.prizes = prizes or []

    def execute(self, query, params=()):
        self.executions.append((query, params))
        if query.startswith('INSERT INTO customers'):
            return FakeCursor({'id': 42})
        if query.startswith('SELECT * FROM reward_prizes'):
            return FakeCursor(rows=self.prizes)
        return FakeCursor()

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
        self.client = app_module.app.test_client()

    def test_registration_activates_account_and_awards_first_spin(self):
        connection = FakeConnection()
        registration = {
            'name': 'Teste Cliente',
            'whatsapp': '(41) 99999-9999',
            'email': 'cliente@example.com',
            'cpf': '529.982.247-25',
            'password': 'senha-segura-123',
        }

        with (
            patch.object(app_module, 'REQUIRE_EMAIL_VERIFICATION', False),
            patch.object(app_module, 'get_db', return_value=connection),
            patch.object(app_module, 'send_account_email') as send_email,
        ):
            response = self.client.post('/api/auth/register', json=registration)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['customerId'], 42)
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)
        self.assertEqual(len(connection.executions), 3)
        customer_insert = connection.executions[0]
        spin_insert = connection.executions[2]
        self.assertIn('email_verified', customer_insert[0])
        self.assertEqual(customer_insert[1][5], 1)
        self.assertIn("'signup', 'pending'", spin_insert[0])
        send_email.assert_not_called()
        with self.client.session_transaction() as session:
            self.assertEqual(session['customer_id'], 42)

    def test_public_pages_and_admin_separation(self):
        home = self.client.get('/')
        page = self.client.get('/roleta.html')
        script = self.client.get('/roleta.js')
        admin_page = self.client.get('/admin.html')
        guide = self.client.get('/guia.html')

        self.assertEqual(home.status_code, 200)
        self.assertIn(b'href="/admin.html"', home.data)
        self.assertNotIn(b'id="adminLoginForm"', home.data)
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'id="spinButton"', page.data)
        self.assertEqual(script.status_code, 200)
        self.assertEqual(admin_page.status_code, 200)
        self.assertIn(b'id="adminLoginForm"', admin_page.data)
        self.assertIn(b'name="robots" content="noindex, nofollow"', admin_page.data)
        self.assertEqual(guide.status_code, 404)

        public_files = (
            '/styles.css',
            '/login.js',
            '/script.js',
            '/admin.js',
            '/njnaruto.ttf',
            '/esqueci-senha.html',
            '/roleta.js',
        )
        for path in public_files:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            response.close()

        public_assets = (
            '/assets/img/logo.png',
            '/assets/img/banner.png',
            '/assets/img/obt.mp4',
            '/assets/img/obtmsc.mp3',
            '/assets/img/cadastro.mp3',
        )
        for path in public_assets:
            response = self.client.head(path)
            self.assertEqual(response.status_code, 200, path)
            response.close()

        home.close()
        page.close()
        script.close()
        admin_page.close()
        guide.close()

    def test_protected_api_routes_reject_unauthenticated_requests_without_database(self):
        requests = [
            ('get', '/api/admin/me'),
            ('get', '/api/admin/customers'),
            ('put', '/api/admin/customers/1'),
            ('put', '/api/admin/customers/1/password'),
            ('delete', '/api/admin/customers/1'),
            ('get', '/api/admin/prizes'),
            ('put', '/api/admin/prizes'),
            ('post', '/api/tattoos/approve'),
            ('get', '/api/customers/1'),
            ('get', '/api/customers/1/loyalty'),
            ('post', '/api/spins/roll'),
            ('post', '/api/tattoos/request'),
            ('get', '/uploads/private.png'),
        ]

        with patch.object(
            app_module,
            'get_db',
            side_effect=AssertionError('Database access was not expected'),
        ):
            for method, path in requests:
                request = getattr(self.client, method)
                response = (
                    request(path, json={})
                    if method in {'post', 'put'}
                    else request(path)
                )
                self.assertEqual(response.status_code, 401, path)

    def test_public_status_and_session_routes_do_not_need_database(self):
        with patch.object(
            app_module,
            'get_db',
            side_effect=AssertionError('Database access was not expected'),
        ):
            self.assertEqual(self.client.get('/api/health').status_code, 200)
            session = self.client.get('/api/auth/me')
            self.assertEqual(session.status_code, 200)
            self.assertIsNone(session.get_json()['customer'])
            self.assertEqual(self.client.post('/api/auth/logout').status_code, 200)
            self.assertEqual(self.client.post('/api/admin/logout').status_code, 200)
            self.assertEqual(self.client.post('/api/customers/register').status_code, 410)

    def test_public_preview_spins_repeatedly_without_creating_real_coupons(self):
        prize = {
            'id': 1,
            'name': 'Prêmio demonstrativo',
            'discount_percent': 10,
            'tomoe_level': 1,
            'probability_weight': 1,
            'active': 1,
        }
        connections = [FakeConnection(prizes=[prize]) for _ in range(3)]

        with patch.object(app_module, 'get_db', side_effect=connections):
            responses = [
                self.client.post('/api/spins/preview', json={})
                for _ in range(3)
            ]

        for response, connection in zip(responses, connections):
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()['preview'])
            self.assertEqual(response.get_json()['result']['prizeName'], prize['name'])
            self.assertNotIn('coupon', response.get_json())
            self.assertEqual(len(connection.executions), 1)
            self.assertIn('SELECT * FROM reward_prizes', connection.executions[0][0])
            self.assertFalse(connection.committed)
            self.assertTrue(connection.closed)
