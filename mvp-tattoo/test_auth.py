"""Testes de integração das contas, permissões, roleta e fidelidade."""
import os
import re
import unittest
import uuid
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import make_dsn, parse_dsn
from psycopg2.extras import RealDictCursor

os.environ.setdefault('FLASK_SECRET_KEY', 'test-session-secret')
os.environ.setdefault('ADMIN_USERNAME', 'test-admin')
os.environ.setdefault('ADMIN_PASSWORD', 'test-admin-password')
os.environ.setdefault('CPF_HASH_SECRET', 'test-cpf-hash-secret')

import app as app_module


class AccountFlowTests(unittest.TestCase):
    """Executa cada caso em um schema PostgreSQL temporário e isolado."""

    registration = {
        'name': 'Teste Cliente',
        'whatsapp': '(41) 99999-9999',
        'email': 'cliente@example.com',
        'cpf': '529.982.247-25',
        'password': 'senha-segura-123',
    }

    def setUp(self):
        """Cria banco isolado para impedir que os testes alterem dados reais."""
        if not app_module.DATABASE_URL:
            self.fail('Set DATABASE_URL in the project .env before running database tests.')
        self.schema = f'test_auth_{uuid.uuid4().hex}'
        connection_parameters = parse_dsn(app_module.DATABASE_URL)
        connection_parameters['host'] = connection_parameters['host'].replace(
            '-pooler.', '.'
        )
        self.test_database_url = make_dsn(**connection_parameters)
        self.admin_connection = psycopg2.connect(self.test_database_url)
        self.admin_connection.autocommit = True
        with self.admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema))
            )
        self.addCleanup(self.drop_test_schema)
        self.db_patch = patch.object(app_module, 'get_db', self.get_test_db)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        app_module.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
        app_module.init_db()
        app_module.seed_prizes()
        self.client = app_module.app.test_client()

    def get_test_db(self):
        """Abre conexão apontada ao schema temporário desta execução."""
        connection = psycopg2.connect(
            self.test_database_url,
            cursor_factory=RealDictCursor,
            options=f'-c search_path={self.schema}',
        )
        return app_module.PostgresConnection(connection)

    def drop_test_schema(self):
        """Remove ao final o schema criado pelo teste."""
        with self.admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(
                    sql.Identifier(self.schema)
                )
            )
        self.admin_connection.close()

    def register_and_verify(self):
        """Cadastra cliente com envio de e-mail simulado e devolve o token."""
        with patch.object(app_module, 'send_account_email') as send_email:
            response = self.client.post('/api/auth/register', json=self.registration)
        self.assertEqual(response.status_code, 202)
        body = send_email.call_args.args[2]
        link = re.search(r'https?://\S+', body).group(0)
        token = parse_qs(urlparse(link).query)['verificar'][0]
        return token

    def test_cpf_checksum(self):
        """Confere CPF válido, sequência repetida e dígito verificador incorreto."""
        self.assertTrue(app_module.valid_cpf('529.982.247-25'))
        self.assertFalse(app_module.valid_cpf('111.111.111-11'))
        self.assertFalse(app_module.valid_cpf('529.982.247-24'))

    def test_registration_verification_login_and_spin(self):
        """Percorre cadastro, proteção dos dados, confirmação, login e giro."""
        invalid = dict(self.registration, cpf='52998224724')
        response = self.client.post('/api/auth/register', json=invalid)
        self.assertEqual(response.status_code, 400)

        token = self.register_and_verify()
        conn = app_module.get_db()
        stored = conn.execute(
            'SELECT cpf_hash, password_hash, verification_token_hash FROM customers'
        ).fetchone()
        self.assertNotIn('52998224725', stored['cpf_hash'])
        self.assertNotEqual(stored['password_hash'], self.registration['password'])
        self.assertNotEqual(stored['verification_token_hash'], token)
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
        """Confere duplicidade, separação de papéis e minimização de dados."""
        self.register_and_verify()
        duplicate = dict(self.registration, email='other@example.com', whatsapp='41988887777')
        response = self.client.post('/api/auth/register', json=duplicate)
        self.assertEqual(response.status_code, 409)

        customer_cannot_use_developer_login = self.client.post('/api/admin/login', json={
            'username': self.registration['email'],
            'password': self.registration['password'],
        })
        self.assertEqual(customer_cannot_use_developer_login.status_code, 401)
        unauthorized = self.client.get('/api/admin/customers')
        self.assertEqual(unauthorized.status_code, 401)
        admin_login = self.client.post('/api/admin/login', json={
            'username': 'test-admin',
            'password': 'test-admin-password',
        })
        self.assertEqual(admin_login.status_code, 200)
        conn = app_module.get_db()
        admin_password_hash = conn.execute(
            'SELECT password_hash FROM developer_admins WHERE username = %s',
            ('test-admin',),
        ).fetchone()['password_hash']
        self.assertNotEqual(admin_password_hash, 'test-admin-password')
        self.assertTrue(
            app_module.check_password_hash(admin_password_hash, 'test-admin-password')
        )
        conn.close()
        customers = self.client.get('/api/admin/customers').get_json()['customers']
        self.assertEqual(len(customers), 1)
        self.assertNotIn('cpf_hash', customers[0])
        self.assertNotIn('password_hash', customers[0])
        self.assertNotIn('verification_token_hash', customers[0])

    def test_admin_can_edit_reset_and_delete_customer(self):
        """Confere edição, redefinição e exclusão protegidas por sessão admin."""
        token = self.register_and_verify()
        self.assertEqual(
            self.client.post('/api/auth/verify-email', json={'token': token}).status_code,
            200,
        )
        customer_id = self.client.get('/api/auth/me').get_json()['customer']['id']
        self.assertEqual(
            self.client.put(
                f'/api/admin/customers/{customer_id}/password',
                json={'password': 'nova-senha-segura'},
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post('/api/admin/login', json={
                'username': 'test-admin',
                'password': 'test-admin-password',
            }).status_code,
            200,
        )

        updated = self.client.put(f'/api/admin/customers/{customer_id}', json={
            'name': 'Nome corrigido',
            'email': 'corrigido@example.com',
            'whatsapp': '(41) 98888-7777',
        })
        self.assertEqual(updated.status_code, 200)
        customer = self.client.get('/api/admin/customers').get_json()['customers'][0]
        self.assertEqual(customer['name'], 'Nome corrigido')
        self.assertEqual(customer['email'], 'corrigido@example.com')
        self.assertEqual(customer['whatsapp'], '41988887777')
        self.assertEqual(customer['email_verified'], 0)

        invalid_password = self.client.put(
            f'/api/admin/customers/{customer_id}/password',
            json={'password': 'curta'},
        )
        self.assertEqual(invalid_password.status_code, 400)
        reset = self.client.put(
            f'/api/admin/customers/{customer_id}/password',
            json={'password': 'nova-senha-segura'},
        )
        self.assertEqual(reset.status_code, 200)

        conn = app_module.get_db()
        spin_id = conn.execute(
            'SELECT id FROM customer_spins WHERE customer_id = %s',
            (customer_id,),
        ).fetchone()['id']
        conn.execute(
            'INSERT INTO tattoo_sessions (customer_id) VALUES (%s)',
            (customer_id,),
        )
        conn.execute(
            'UPDATE loyalty_progress SET completed_tattoos = 1 WHERE customer_id = %s',
            (customer_id,),
        )
        conn.execute(
            'INSERT INTO tattoo_requests (customer_id, description) VALUES (%s, %s)',
            (customer_id, 'Solicitação de teste'),
        )
        conn.execute(
            'INSERT INTO coupons (customer_id, spin_id, code, discount_percent) '
            'VALUES (%s, %s, %s, %s)',
            (customer_id, spin_id, 'TESTE-EXCLUSAO', 5),
        )
        conn.commit()
        conn.close()

        deleted = self.client.delete(f'/api/admin/customers/{customer_id}')
        self.assertEqual(deleted.status_code, 200)
        missing = self.client.delete(f'/api/admin/customers/{customer_id}')
        self.assertEqual(missing.status_code, 404)
        conn = app_module.get_db()
        remaining_customer = conn.execute(
            'SELECT COUNT(*) AS count FROM customers WHERE id = %s',
            (customer_id,),
        ).fetchone()['count']
        self.assertEqual(remaining_customer, 0)
        for table in (
            'customer_spins',
            'tattoo_sessions',
            'loyalty_progress',
            'tattoo_requests',
            'coupons',
        ):
            remaining = conn.execute(
                f'SELECT COUNT(*) AS count FROM {table} WHERE customer_id = %s',
                (customer_id,),
            ).fetchone()['count']
            self.assertEqual(remaining, 0, table)
        conn.close()

    def test_admin_can_manage_prizes_and_public_wheel_settings(self):
        """Confere atualização dos prêmios e validação de ao menos um ativo."""
        self.assertEqual(self.client.get('/api/admin/prizes').status_code, 401)
        self.assertEqual(
            self.client.post('/api/admin/login', json={
                'username': 'test-admin',
                'password': 'test-admin-password',
            }).status_code,
            200,
        )
        prizes = self.client.get('/api/admin/prizes').get_json()['prizes']
        prizes_for_update = [
            {
                'id': prize['id'],
                'name': prize['name'],
                'discountPercent': prize['discount_percent'],
                'tomoeLevel': prize['tomoe_level'],
                'probabilityWeight': prize['probability_weight'],
                'active': bool(prize['active']),
            }
            for prize in prizes
        ]
        prizes_for_update[0]['name'] = 'Desconto especial'
        prizes_for_update[0]['discountPercent'] = 12.5
        prizes_for_update[0]['probabilityWeight'] = 20
        saved = self.client.put('/api/admin/prizes', json={'prizes': prizes_for_update})
        self.assertEqual(saved.status_code, 200)

        public_prizes = self.client.get('/api/prizes').get_json()['prizes']
        self.assertEqual(public_prizes[0]['name'], 'Desconto especial')
        self.assertEqual(public_prizes[0]['discount_percent'], 12.5)
        self.assertEqual(public_prizes[0]['probability_weight'], 20)

        for prize in prizes_for_update:
            prize['active'] = False
        invalid = self.client.put('/api/admin/prizes', json={'prizes': prizes_for_update})
        self.assertEqual(invalid.status_code, 400)

    def test_tattoo_request_and_loyalty_milestone(self):
        """Confere pedido de tatuagem e concessão de giro no terceiro marco."""
        token = self.register_and_verify()
        self.assertEqual(
            self.client.post('/api/auth/verify-email', json={'token': token}).status_code,
            200,
        )
        customer = self.client.get('/api/auth/me').get_json()['customer']
        request_response = self.client.post('/api/tattoos/request', json={
            'title': 'Primeira ideia',
            'description': 'Uma ideia de teste.',
            'bodyPart': 'braço',
            'size': 'pequena',
        })
        self.assertEqual(request_response.status_code, 201)
        customer_data = self.client.get(
            f'/api/customers/{customer["id"]}'
        ).get_json()
        self.assertEqual(len(customer_data['requests']), 1)

        self.assertEqual(
            self.client.post('/api/admin/login', json={
                'username': 'test-admin',
                'password': 'test-admin-password',
            }).status_code,
            200,
        )
        for expected_spins in (0, 0, 1):
            approval = self.client.post('/api/tattoos/approve', json={
                'customerId': customer['id'],
            })
            self.assertEqual(approval.status_code, 200)
            self.assertEqual(approval.get_json()['newSpins'], expected_spins)

        self.assertEqual(
            self.client.post('/api/auth/login', json={
                'identifier': self.registration['email'],
                'password': self.registration['password'],
            }).status_code,
            200,
        )
        loyalty = self.client.get(
            f'/api/customers/{customer["id"]}/loyalty'
        ).get_json()['loyalty']
        self.assertEqual(loyalty['completed_tattoos'], 3)
        self.assertEqual(loyalty['available_spins'], 1)

    def test_resend_verification_by_cpf(self):
        """Confere reenvio da confirmação usando CPF e senha do cliente."""
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
        """Confere recuperação, nova senha, páginas públicas e rotas antigas."""
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

        for path in ('/', '/esqueci-senha.html'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            response.close()
        for path in ('/mvp', '/mvp/'):
            response = self.client.get(path, follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/')
            response.close()
        assets = self.client.get('/mvp-assets/app.js')
        self.assertEqual(assets.status_code, 200)
        assets.close()
        admin_script = self.client.get('/admin.js')
        self.assertEqual(admin_script.status_code, 200)
        admin_script.close()
        self.assertEqual(self.client.get('/api/prizes').status_code, 200)
        self.assertEqual(self.client.get('/mvp-tattoo/data.sqlite').status_code, 404)


if __name__ == '__main__':
    unittest.main()
