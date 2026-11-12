from __future__ import annotations

import json
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import threading
import uuid
import webbrowser
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, request, send_from_directory, session
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
WEB_ROOT = BASE_DIR.parent
load_dotenv(WEB_ROOT / '.env')
DATABASE_URL = os.environ.get('DATABASE_URL')
STATIC_DIR = BASE_DIR / 'public'
UPLOAD_FOLDER = BASE_DIR / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE') == '1'

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
CPF_HASH_SECRET = os.environ.get('CPF_HASH_SECRET')

if not app.secret_key or not CPF_HASH_SECRET:
    raise RuntimeError(
        'Set FLASK_SECRET_KEY and CPF_HASH_SECRET environment variables.'
    )


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, parameters)
        return cursor

    def executemany(self, query, parameters):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.executemany(query, parameters)
        return cursor

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def get_db():
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL must be set in the environment or project .env file.')
    return PostgresConnection(
        psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    )


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get('admin_role') != 'developer':
            return jsonify({'error': 'Sem autorização de administrador.'}), 401
        return view(*args, **kwargs)
    return wrapped


def customer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        customer_id = session.get('customer_id')
        if not customer_id:
            return jsonify({'error': 'Entre na sua conta para continuar.'}), 401
        conn = get_db()
        customer = conn.execute(
            'SELECT id FROM customers WHERE id = %s AND email_verified = 1',
            (customer_id,),
        ).fetchone()
        conn.close()
        if not customer:
            session.pop('customer_id', None)
            return jsonify({'error': 'Entre na sua conta para continuar.'}), 401
        return view(*args, **kwargs)
    return wrapped


def valid_cpf(value):
    cpf = re.sub(r'\D', '', str(value or ''))
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    digits = [int(char) for char in cpf]
    for length in (9, 10):
        weight = length + 1
        total = sum(digits[index] * (weight - index) for index in range(length))
        check_digit = (total * 10) % 11
        if check_digit == 10:
            check_digit = 0
        if digits[length] != check_digit:
            return False
    return True


def cpf_digest(value):
    normalized = re.sub(r'\D', '', value)
    return hmac.new(CPF_HASH_SECRET.encode(), normalized.encode(), hashlib.sha256).hexdigest()


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def send_account_email(recipient, subject, body):
    host = os.environ.get('SMTP_HOST')
    sender = os.environ.get('SMTP_FROM')
    if not host or not sender:
        raise RuntimeError('Confirme o e-mail somente depois de configurar SMTP_HOST e SMTP_FROM.')

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = recipient
    message.set_content(body)

    port = int(os.environ.get('SMTP_PORT', '587'))
    username = os.environ.get('SMTP_USERNAME')
    password = os.environ.get('SMTP_PASSWORD')
    if os.environ.get('SMTP_USE_SSL') == '1':
        with smtplib.SMTP_SSL(host, port, timeout=15) as server:
            if username:
                server.login(username, password or '')
            server.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=15) as server:
        server.ehlo()
        if os.environ.get('SMTP_USE_TLS', '1') == '1':
            server.starttls()
            server.ehlo()
        if username:
            server.login(username, password or '')
        server.send_message(message)


def init_db():
    conn = get_db()
    schema_statements = (
        """CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            whatsapp TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            email TEXT,
            cpf_hash TEXT,
            password_hash TEXT,
            email_verified INTEGER NOT NULL DEFAULT 0,
            verification_token_hash TEXT,
            verification_expires_at TIMESTAMPTZ,
            password_reset_token_hash TEXT,
            password_reset_expires_at TIMESTAMPTZ
        )""",
        """CREATE TABLE IF NOT EXISTS developer_admins (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'developer',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS reward_prizes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            discount_percent DOUBLE PRECISION NOT NULL,
            tomoe_level INTEGER NOT NULL,
            probability_weight INTEGER NOT NULL,
            active INTEGER DEFAULT 1
        )""",
        """CREATE TABLE IF NOT EXISTS customer_spins (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            prize_id INTEGER,
            source TEXT NOT NULL DEFAULT 'signup',
            status TEXT NOT NULL DEFAULT 'pending',
            rolled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            random_seed TEXT,
            server_result TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )""",
        """CREATE TABLE IF NOT EXISTS tattoo_sessions (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            admin_name TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            approved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )""",
        """CREATE TABLE IF NOT EXISTS loyalty_progress (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER UNIQUE NOT NULL,
            completed_tattoos INTEGER DEFAULT 0,
            available_spins INTEGER DEFAULT 0,
            last_milestone INTEGER DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )""",
        """CREATE TABLE IF NOT EXISTS tattoo_requests (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            title TEXT,
            description TEXT NOT NULL,
            body_part TEXT,
            size TEXT,
            reference_image_url TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )""",
        """CREATE TABLE IF NOT EXISTS coupons (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            spin_id INTEGER,
            code TEXT UNIQUE NOT NULL,
            discount_percent DOUBLE PRECISION NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(spin_id) REFERENCES customer_spins(id)
        )""",
    )
    for statement in schema_statements:
        conn.execute(statement)
    columns = {
        row['column_name']
        for row in conn.execute(
            'SELECT column_name FROM information_schema.columns '
            'WHERE table_schema = current_schema() AND table_name = %s',
            ('customers',),
        ).fetchall()
    }
    account_columns = {
        'email': 'TEXT',
        'cpf_hash': 'TEXT',
        'password_hash': 'TEXT',
        'email_verified': 'INTEGER NOT NULL DEFAULT 0',
        'verification_token_hash': 'TEXT',
        'verification_expires_at': 'TIMESTAMPTZ',
        'password_reset_token_hash': 'TEXT',
        'password_reset_expires_at': 'TIMESTAMPTZ',
    }
    for name, definition in account_columns.items():
        if name not in columns:
            conn.execute(f'ALTER TABLE customers ADD COLUMN {name} {definition}')
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_email ON customers(email) "
        "WHERE email IS NOT NULL AND email <> ''"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_cpf_hash ON customers(cpf_hash) "
        "WHERE cpf_hash IS NOT NULL AND cpf_hash <> ''"
    )
    if ADMIN_USERNAME and ADMIN_PASSWORD:
        conn.execute(
            'INSERT INTO developer_admins (username, password_hash) '
            'SELECT %s, %s WHERE NOT EXISTS (SELECT 1 FROM developer_admins)',
            (
                ADMIN_USERNAME.strip().lower(),
                generate_password_hash(ADMIN_PASSWORD),
            ),
        )
    conn.commit()
    conn.close()


def seed_prizes():
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) AS total FROM reward_prizes').fetchone()['total']
    if count > 0:
        conn.close()
        return

    prizes = [
        ('1 Tomoe', 5, 1, 35),
        ('2 Tomoes', 10, 2, 25),
        ('3 Tomoes', 15, 3, 18),
        ('Sharingan 1', 20, 3, 12),
        ('Sharingan 2', 30, 3, 7),
        ('Lenda', 40, 3, 3),
    ]

    conn.executemany(
        'INSERT INTO reward_prizes (name, discount_percent, tomoe_level, probability_weight, active) VALUES (%s, %s, %s, %s, 1)',
        prizes,
    )
    conn.commit()
    conn.close()


def customer_summary(customer):
    return {
        'id': customer['id'],
        'whatsapp': customer['whatsapp'],
        'name': customer['name'],
        'created_at': customer['created_at'],
    }


def pick_weighted_prize():
    conn = get_db()
    prizes = conn.execute('SELECT * FROM reward_prizes WHERE active = 1 ORDER BY id').fetchall()
    conn.close()

    if not prizes:
        raise RuntimeError('Nenhum prêmio ativo encontrado.')

    total_weight = sum(int(p['probability_weight']) for p in prizes)
    value = secrets.randbelow(total_weight) + 1
    cursor = 0

    for prize in prizes:
        cursor += int(prize['probability_weight'])
        if value <= cursor:
            return dict(prize)

    return dict(prizes[0])


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    if session.get('admin_role') != 'developer' and not session.get('customer_id'):
        return jsonify({'error': 'Entre na sua conta para acessar este arquivo.'}), 401
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/health')
def health():
    return jsonify({'ok': True, 'message': 'Tattoo MVP online'})


@app.route('/api/prizes', methods=['GET'])
def public_prizes():
    conn = get_db()
    prizes = conn.execute(
        'SELECT id, name, discount_percent, tomoe_level, probability_weight '
        'FROM reward_prizes WHERE active = 1 ORDER BY id'
    ).fetchall()
    conn.close()
    return jsonify({'prizes': [dict(prize) for prize in prizes]})


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get('username') or '').strip().lower()
    password = payload.get('password') or ''
    if not isinstance(password, str):
        return jsonify({'error': 'Credenciais inválidas.'}), 401

    conn = get_db()
    admin = conn.execute(
        "SELECT id, username, password_hash, role FROM developer_admins "
        "WHERE username = %s AND role = 'developer'",
        (username,),
    ).fetchone()
    conn.close()
    if admin and check_password_hash(admin['password_hash'], password):
        session.clear()
        session['admin_user_id'] = admin['id']
        session['admin_user'] = admin['username']
        session['admin_role'] = admin['role']
        return jsonify({'ok': True, 'user': admin['username']})

    return jsonify({'error': 'Credenciais inválidas.'}), 401


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/admin/me', methods=['GET'])
def admin_me():
    if session.get('admin_role') != 'developer':
        return jsonify({'error': 'Não autenticado.'}), 401
    return jsonify({'ok': True, 'user': session.get('admin_user')})


@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get('name') or '').strip()
    whatsapp = re.sub(r'\D', '', str(payload.get('whatsapp') or ''))
    email = str(payload.get('email') or '').strip().lower()
    cpf = re.sub(r'\D', '', str(payload.get('cpf') or ''))
    password = payload.get('password') or ''

    if not name or len(name) > 120 or len(whatsapp) not in (10, 11):
        return jsonify({'error': 'Informe um nome e um telefone com DDD válidos.'}), 400
    if not isinstance(password, str):
        return jsonify({'error': 'A senha informada é inválida.'}), 400
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        return jsonify({'error': 'Informe um e-mail válido.'}), 400
    if not valid_cpf(cpf):
        return jsonify({'error': 'CPF inválido. Confira os dígitos informados.'}), 400
    if len(password) < 8:
        return jsonify({'error': 'A senha deve ter pelo menos 8 caracteres.'}), 400

    verification_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO customers
               (whatsapp, name, email, cpf_hash, password_hash,
                verification_token_hash, verification_expires_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (
                whatsapp,
                name,
                email,
                cpf_digest(cpf),
                generate_password_hash(password),
                token_digest(verification_token),
                expires_at,
            ),
        )
        customer_id = cursor.fetchone()['id']
        conn.commit()
    except psycopg2.IntegrityError:
        conn.close()
        return jsonify({'error': 'CPF, e-mail ou telefone já cadastrado.'}), 409
    conn.close()

    base_url = os.environ.get('PUBLIC_BASE_URL', request.host_url).rstrip('/')
    verification_url = f'{base_url}/?verificar={verification_token}'
    try:
        send_account_email(
            email,
            'Confirme seu e-mail - Roleta da Fidelidade',
            f'Olá, {name}!\n\nConfirme seu e-mail neste link (válido por 1 hora):\n{verification_url}',
        )
    except (OSError, RuntimeError, smtplib.SMTPException, ValueError) as error:
        app.logger.error('Falha ao enviar confirmação de e-mail: %s', error)
        return jsonify({
            'error': 'Não foi possível enviar o e-mail de confirmação. Configure o serviço de e-mail e tente novamente.'
        }), 503

    return jsonify({
        'ok': True,
        'message': 'Enviamos um link de confirmação para seu e-mail. Ele expira em 1 hora.',
        'customerId': customer_id,
    }), 202


@app.route('/api/auth/resend-verification', methods=['POST'])
def resend_verification():
    payload = request.get_json(silent=True) or {}
    identifier = str(payload.get('identifier') or payload.get('email') or '').strip()
    password = payload.get('password') or ''
    if not isinstance(password, str):
        return jsonify({'error': 'Conta pendente não encontrada ou senha incorreta.'}), 400
    conn = get_db()
    if '@' in identifier:
        customer = conn.execute(
            'SELECT id, name, email, password_hash, email_verified FROM customers WHERE email = %s',
            (identifier.lower(),),
        ).fetchone()
    else:
        cpf = re.sub(r'\D', '', identifier)
        if not valid_cpf(cpf):
            conn.close()
            return jsonify({'error': 'Conta pendente não encontrada ou senha incorreta.'}), 400
        customer = conn.execute(
            'SELECT id, name, email, password_hash, email_verified FROM customers WHERE cpf_hash = %s',
            (cpf_digest(cpf),),
        ).fetchone()
    if (
        not customer
        or customer['email_verified']
        or not customer['email']
        or not customer['password_hash']
        or not check_password_hash(customer['password_hash'], password)
    ):
        conn.close()
        return jsonify({'error': 'Conta pendente não encontrada ou senha incorreta.'}), 400

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    conn.execute(
        'UPDATE customers SET verification_token_hash = %s, verification_expires_at = %s WHERE id = %s',
        (token_digest(token), expires_at, customer['id']),
    )
    conn.commit()
    conn.close()
    base_url = os.environ.get('PUBLIC_BASE_URL', request.host_url).rstrip('/')
    try:
        send_account_email(
            customer['email'],
            'Confirme seu e-mail - Roleta da Fidelidade',
            f'Olá, {customer["name"]}!\n\nConfirme seu e-mail neste link (válido por 1 hora):\n{base_url}/?verificar={token}',
        )
    except (OSError, RuntimeError, smtplib.SMTPException, ValueError) as error:
        app.logger.error('Falha ao reenviar confirmação de e-mail: %s', error)
        return jsonify({'error': 'Serviço de e-mail indisponível. Tente novamente mais tarde.'}), 503
    return jsonify({'ok': True, 'message': 'Enviamos um novo link de confirmação.'})


@app.route('/api/auth/verify-email', methods=['POST'])
def verify_email():
    payload = request.get_json(silent=True) or {}
    token = payload.get('token') or ''
    if not isinstance(token, str) or not token:
        return jsonify({'error': 'Link de confirmação inválido.'}), 400
    conn = get_db()
    customer = conn.execute(
        """SELECT id, name FROM customers
           WHERE verification_token_hash = %s AND verification_expires_at > %s""",
        (token_digest(token), datetime.now(timezone.utc)),
    ).fetchone()
    if not customer:
        conn.close()
        return jsonify({'error': 'Link inválido ou expirado. Solicite outro link de confirmação.'}), 400
    conn.execute(
        """UPDATE customers SET email_verified = 1, verification_token_hash = NULL,
           verification_expires_at = NULL WHERE id = %s""",
        (customer['id'],),
    )
    conn.execute(
        'INSERT INTO loyalty_progress (customer_id) VALUES (%s) '
        'ON CONFLICT (customer_id) DO NOTHING',
        (customer['id'],),
    )
    conn.execute(
        """INSERT INTO customer_spins (customer_id, source, status, expires_at)
           VALUES (%s, 'signup', 'pending', %s)""",
        (customer['id'], datetime.now(timezone.utc) + timedelta(days=30)),
    )
    conn.commit()
    conn.close()
    session.clear()
    session['customer_id'] = customer['id']
    return jsonify({'ok': True, 'message': 'E-mail confirmado. Seu primeiro giro está disponível.'})


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    payload = request.get_json(silent=True) or {}
    identifier = str(payload.get('identifier') or '').strip()
    password = payload.get('password') or ''
    if not isinstance(password, str):
        return jsonify({'error': 'Dados de acesso incorretos.'}), 401
    if '@' in identifier:
        conn = get_db()
        customer = conn.execute(
            'SELECT id, password_hash, email_verified FROM customers WHERE email = %s',
            (identifier.lower(),),
        ).fetchone()
    else:
        cpf = re.sub(r'\D', '', identifier)
        if not valid_cpf(cpf):
            return jsonify({'error': 'Informe um e-mail ou CPF válido.'}), 400
        conn = get_db()
        customer = conn.execute(
            'SELECT id, password_hash, email_verified FROM customers WHERE cpf_hash = %s',
            (cpf_digest(cpf),),
        ).fetchone()
    conn.close()
    if not customer or not customer['password_hash'] or not check_password_hash(customer['password_hash'], password):
        return jsonify({'error': 'Dados de acesso incorretos.'}), 401
    if not customer['email_verified']:
        return jsonify({'error': 'Confirme seu e-mail antes de entrar.'}), 403
    session.clear()
    session['customer_id'] = customer['id']
    return jsonify({'ok': True, 'customerId': customer['id']})


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    customer_id = session.get('customer_id')
    if not customer_id:
        return jsonify({'ok': True, 'customer': None})
    conn = get_db()
    customer = conn.execute(
        'SELECT id, name, email, whatsapp, email_verified FROM customers WHERE id = %s',
        (customer_id,),
    ).fetchone()
    conn.close()
    if not customer or not customer['email_verified']:
        session.pop('customer_id', None)
        return jsonify({'ok': True, 'customer': None})
    customer = {key: customer[key] for key in ('id', 'name', 'email', 'whatsapp')}
    return jsonify({'ok': True, 'customer': dict(customer)})


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/auth/password-reset', methods=['POST'])
def request_password_reset():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get('email') or '').strip().lower()
    conn = get_db()
    customer = conn.execute(
        'SELECT id, name FROM customers WHERE email = %s AND email_verified = 1',
        (email,),
    ).fetchone()
    if not customer:
        conn.close()
        return jsonify({'ok': True, 'message': 'Se o e-mail estiver cadastrado, enviaremos as instruções.'})

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    conn.execute(
        'UPDATE customers SET password_reset_token_hash = %s, password_reset_expires_at = %s WHERE id = %s',
        (token_digest(token), expires_at, customer['id']),
    )
    conn.commit()
    conn.close()
    base_url = os.environ.get('PUBLIC_BASE_URL', request.host_url).rstrip('/')
    reset_url = f'{base_url}/esqueci-senha.html?token={token}'
    try:
        send_account_email(
            email,
            'Redefina sua senha - Roleta da Fidelidade',
            f'Olá, {customer["name"]}!\n\nRedefina sua senha neste link (válido por 30 minutos):\n{reset_url}',
        )
    except (OSError, RuntimeError, smtplib.SMTPException, ValueError) as error:
        app.logger.error('Falha ao enviar recuperação de senha: %s', error)
        return jsonify({'error': 'Serviço de e-mail indisponível. Tente novamente mais tarde.'}), 503
    return jsonify({'ok': True, 'message': 'Se o e-mail estiver cadastrado, enviaremos as instruções.'})


@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    payload = request.get_json(silent=True) or {}
    token = payload.get('token') or ''
    password = payload.get('password') or ''
    if not isinstance(token, str) or not isinstance(password, str) or len(password) < 8:
        return jsonify({'error': 'A senha deve ter pelo menos 8 caracteres.'}), 400
    conn = get_db()
    customer = conn.execute(
        """SELECT id FROM customers
           WHERE password_reset_token_hash = %s AND password_reset_expires_at > %s""",
        (token_digest(token), datetime.now(timezone.utc)),
    ).fetchone()
    if not customer:
        conn.close()
        return jsonify({'error': 'Link inválido ou expirado. Solicite uma nova recuperação.'}), 400
    conn.execute(
        """UPDATE customers SET password_hash = %s, password_reset_token_hash = NULL,
           password_reset_expires_at = NULL WHERE id = %s""",
        (generate_password_hash(password), customer['id']),
    )
    conn.commit()
    conn.close()
    session.clear()
    return jsonify({'ok': True, 'message': 'Senha alterada. Entre com sua nova senha.'})


@app.route('/api/customers/register', methods=['POST'])
def register_customer():
    return jsonify({'error': 'Use o cadastro com CPF e confirmação de e-mail.'}), 410


@app.route('/api/customers/<int:customer_id>', methods=['GET'])
@customer_required
def get_customer(customer_id):
    if customer_id != session.get('customer_id'):
        return jsonify({'error': 'Sem autorização.'}), 403
    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = %s', (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return jsonify({'error': 'Cliente não encontrado.'}), 404

    spins = conn.execute(
        'SELECT * FROM customer_spins WHERE customer_id = %s ORDER BY rolled_at DESC',
        (customer_id,),
    ).fetchall()
    requests = conn.execute(
        'SELECT * FROM tattoo_requests WHERE customer_id = %s ORDER BY created_at DESC',
        (customer_id,),
    ).fetchall()
    loyalty = conn.execute('SELECT * FROM loyalty_progress WHERE customer_id = %s', (customer_id,)).fetchone()
    conn.close()
    return jsonify({
        'customer': customer_summary(customer),
        'spins': [dict(row) for row in spins],
        'requests': [dict(row) for row in requests],
        'loyalty': dict(loyalty) if loyalty else {'completed_tattoos': 0, 'available_spins': 0, 'last_milestone': 0},
    })


@app.route('/api/spins/roll', methods=['POST'])
@customer_required
def roll_spin():
    payload = request.get_json(silent=True) or {}
    customer_id = session['customer_id']
    supplied_customer_id = payload.get('customerId')
    if supplied_customer_id is not None and str(supplied_customer_id) != str(customer_id):
        return jsonify({'error': 'Sem autorização.'}), 403

    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = %s', (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return jsonify({'error': 'Cliente não encontrado.'}), 404

    pending_spin = conn.execute(
        'SELECT * FROM customer_spins WHERE customer_id = %s AND status = %s ORDER BY rolled_at ASC LIMIT 1',
        (customer_id, 'pending'),
    ).fetchone()
    if not pending_spin:
        conn.close()
        return jsonify({'error': 'Nenhuma rodada disponível.'}), 400

    prize = pick_weighted_prize()
    result = {
        'prizeId': prize['id'],
        'segmentIndex': conn.execute(
            'SELECT COUNT(*) AS segment_index FROM reward_prizes WHERE active = 1 AND id < %s',
            (prize['id'],),
        ).fetchone()['segment_index'],
        'prizeName': prize['name'],
        'discountPercent': float(prize['discount_percent']),
        'tomoeLevel': int(prize['tomoe_level']),
        'rolledAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    db_expires_at = expires_at
    random_seed = str(uuid.uuid4())
    coupon_code = f"TAT-{int(datetime.now(timezone.utc).timestamp() * 1000) % 1000000:06d}"

    conn.execute(
        'UPDATE customer_spins SET prize_id = %s, status = %s, used_at = CURRENT_TIMESTAMP, expires_at = %s, random_seed = %s, server_result = %s WHERE id = %s',
        (prize['id'], 'used', db_expires_at, random_seed, json.dumps(result), pending_spin['id']),
    )
    conn.execute(
        'INSERT INTO coupons (customer_id, spin_id, code, discount_percent, status, expires_at) VALUES (%s, %s, %s, %s, %s, %s)',
        (customer_id, pending_spin['id'], coupon_code, result['discountPercent'], 'active', db_expires_at),
    )
    conn.commit()
    conn.close()

    return jsonify({
        'ok': True,
        'result': result,
        'coupon': {
            'code': coupon_code,
            'discountPercent': result['discountPercent'],
            'expiresAt': expires_at.isoformat().replace('+00:00', 'Z'),
        },
    })


@app.route('/api/admin/customers', methods=['GET'])
@admin_required
def admin_customers():
    conn = get_db()
    customers = conn.execute(
        'SELECT id, name, whatsapp, email, email_verified, created_at '
        'FROM customers ORDER BY created_at DESC'
    ).fetchall()
    sessions = conn.execute('SELECT * FROM tattoo_sessions ORDER BY created_at DESC').fetchall()
    requests = conn.execute('SELECT * FROM tattoo_requests ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify({'customers': [dict(row) for row in customers], 'sessions': [dict(row) for row in sessions], 'requests': [dict(row) for row in requests]})


@app.route('/api/admin/customers/<int:customer_id>', methods=['PUT'])
@admin_required
def admin_update_customer(customer_id):
    payload = request.get_json(silent=True) or {}
    name = str(payload.get('name') or '').strip()
    whatsapp = re.sub(r'\D', '', str(payload.get('whatsapp') or ''))
    email = str(payload.get('email') or '').strip().lower() or None
    if not name or len(name) > 120 or len(whatsapp) not in (10, 11):
        return jsonify({'error': 'Informe nome e telefone com DDD válidos.'}), 400
    if email and not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        return jsonify({'error': 'Informe um e-mail válido.'}), 400

    conn = get_db()
    current = conn.execute(
        'SELECT id, email FROM customers WHERE id = %s',
        (customer_id,),
    ).fetchone()
    if not current:
        conn.close()
        return jsonify({'error': 'Cliente não encontrado.'}), 404

    email_changed = current['email'] != email
    try:
        conn.execute(
            'UPDATE customers SET name = %s, whatsapp = %s, email = %s, '
            'email_verified = CASE WHEN %s THEN 0 ELSE email_verified END, '
            'verification_token_hash = CASE WHEN %s THEN NULL ELSE verification_token_hash END, '
            'verification_expires_at = CASE WHEN %s THEN NULL ELSE verification_expires_at END, '
            'password_reset_token_hash = CASE WHEN %s THEN NULL ELSE password_reset_token_hash END, '
            'password_reset_expires_at = CASE WHEN %s THEN NULL ELSE password_reset_expires_at END '
            'WHERE id = %s',
            (
                name, whatsapp, email, email_changed, email_changed, email_changed,
                email_changed, email_changed, customer_id,
            ),
        )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Este telefone ou e-mail já pertence a outra conta.'}), 409
    conn.close()
    return jsonify({'ok': True, 'message': 'Dados do cliente atualizados.'})


@app.route('/api/admin/customers/<int:customer_id>/password', methods=['PUT'])
@admin_required
def admin_reset_customer_password(customer_id):
    payload = request.get_json(silent=True) or {}
    password = payload.get('password')
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        return jsonify({'error': 'A nova senha deve ter entre 8 e 128 caracteres.'}), 400

    conn = get_db()
    result = conn.execute(
        'UPDATE customers SET password_hash = %s, password_reset_token_hash = NULL, '
        'password_reset_expires_at = NULL WHERE id = %s',
        (generate_password_hash(password), customer_id),
    )
    if result.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Cliente não encontrado.'}), 404
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': 'Senha do cliente redefinida.'})


@app.route('/api/admin/customers/<int:customer_id>', methods=['DELETE'])
@admin_required
def admin_delete_customer(customer_id):
    conn = get_db()
    customer = conn.execute(
        'SELECT id FROM customers WHERE id = %s',
        (customer_id,),
    ).fetchone()
    if not customer:
        conn.close()
        return jsonify({'error': 'Cliente não encontrado.'}), 404

    requests = conn.execute(
        'SELECT reference_image_url FROM tattoo_requests WHERE customer_id = %s',
        (customer_id,),
    ).fetchall()
    image_paths = set()
    for tattoo_request in requests:
        image_url = tattoo_request['reference_image_url'] or ''
        if image_url.startswith('/uploads/'):
            filename = image_url[len('/uploads/'):]
            image_path = UPLOAD_FOLDER / filename
            if filename and Path(filename).name == filename and image_path.resolve().parent == UPLOAD_FOLDER.resolve():
                image_paths.add(image_path)

    conn.execute(
        'DELETE FROM coupons WHERE customer_id = %s OR spin_id IN '
        '(SELECT id FROM customer_spins WHERE customer_id = %s)',
        (customer_id, customer_id),
    )
    conn.execute('DELETE FROM tattoo_requests WHERE customer_id = %s', (customer_id,))
    conn.execute('DELETE FROM tattoo_sessions WHERE customer_id = %s', (customer_id,))
    conn.execute('DELETE FROM loyalty_progress WHERE customer_id = %s', (customer_id,))
    conn.execute('DELETE FROM customer_spins WHERE customer_id = %s', (customer_id,))
    conn.execute('DELETE FROM customers WHERE id = %s', (customer_id,))
    conn.commit()
    conn.close()

    failed_image_deletions = 0
    for image_path in image_paths:
        try:
            image_path.unlink()
        except FileNotFoundError:
            continue
        except OSError as error:
            app.logger.error('Falha ao remover imagem de referência do cliente excluído: %s', error)
            failed_image_deletions += 1
    if failed_image_deletions:
        return jsonify({
            'error': (
                'A conta foi excluída, mas não foi possível remover '
                f'{failed_image_deletions} imagem(ns) de referência.'
            )
        }), 500
    return jsonify({'ok': True, 'message': 'Cliente e dados associados foram excluídos.'})


@app.route('/api/admin/prizes', methods=['GET'])
@admin_required
def admin_prizes():
    conn = get_db()
    prizes = conn.execute(
        'SELECT id, name, discount_percent, tomoe_level, probability_weight, active '
        'FROM reward_prizes ORDER BY id'
    ).fetchall()
    conn.close()
    return jsonify({'prizes': [dict(prize) for prize in prizes]})


@app.route('/api/admin/prizes', methods=['PUT'])
@admin_required
def admin_update_prizes():
    payload = request.get_json(silent=True) or {}
    prizes = payload.get('prizes')
    if not isinstance(prizes, list) or not prizes:
        return jsonify({'error': 'Informe a lista de prêmios.'}), 400

    normalized = []
    seen_ids = set()
    for prize in prizes:
        if not isinstance(prize, dict):
            return jsonify({'error': 'Cada prêmio deve ser um objeto válido.'}), 400
        prize_id = prize.get('id')
        name = str(prize.get('name') or '').strip()
        discount = prize.get('discountPercent')
        weight = prize.get('probabilityWeight')
        tomoe = prize.get('tomoeLevel')
        active = prize.get('active')
        if (
            not isinstance(prize_id, int)
            or isinstance(prize_id, bool)
            or prize_id in seen_ids
            or not name
            or len(name) > 80
            or not isinstance(discount, (int, float))
            or isinstance(discount, bool)
            or not 0 < discount <= 100
            or not isinstance(weight, int)
            or isinstance(weight, bool)
            or not 1 <= weight <= 10000
            or not isinstance(tomoe, int)
            or isinstance(tomoe, bool)
            or not 1 <= tomoe <= 3
            or not isinstance(active, bool)
        ):
            return jsonify({'error': 'Revise nome, desconto, peso e nível de tomoe dos prêmios.'}), 400
        seen_ids.add(prize_id)
        normalized.append((name, float(discount), tomoe, weight, int(active), prize_id))

    if not any(prize[4] for prize in normalized):
        return jsonify({'error': 'Mantenha pelo menos um prêmio ativo.'}), 400

    conn = get_db()
    existing_ids = {
        row['id']
        for row in conn.execute('SELECT id FROM reward_prizes').fetchall()
    }
    if seen_ids != existing_ids:
        conn.close()
        return jsonify({'error': 'A lista deve conter todos os prêmios existentes, sem duplicatas.'}), 400

    conn.executemany(
        'UPDATE reward_prizes SET name = %s, discount_percent = %s, '
        'tomoe_level = %s, probability_weight = %s, active = %s WHERE id = %s',
        normalized,
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': 'Configurações da roleta salvas.'})


@app.route('/api/tattoos/request', methods=['POST'])
@customer_required
def create_tattoo_request():
    customer_id = session['customer_id']
    description = ''
    payload = request.get_json(silent=True) or {}
    if request.files:
        file = request.files.get('referenceImage')
        description = (request.form.get('description') or '').strip()
        title = request.form.get('title') or 'Ideia de tatuagem'
        body_part = request.form.get('bodyPart') or ''
        size = request.form.get('size') or ''
        reference_url = ''
        if file and file.filename:
            original = secure_filename(file.filename)
            safe_name = f"{uuid.uuid4().hex}_{original}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
            file.save(file_path)
            reference_url = f"/uploads/{safe_name}"
        else:
            reference_url = request.form.get('referenceImageUrl') or ''
    else:
        description = (payload.get('description') or '').strip()
        title = payload.get('title') or 'Ideia de tatuagem'
        body_part = payload.get('bodyPart') or ''
        size = payload.get('size') or ''
        reference_url = payload.get('referenceImageUrl') or ''

    if not description:
        return jsonify({'error': 'A descrição é obrigatória.'}), 400

    conn = get_db()
    conn.execute(
        'INSERT INTO tattoo_requests (customer_id, title, description, body_part, size, reference_image_url, status) VALUES (%s, %s, %s, %s, %s, %s, %s)',
        (
            customer_id,
            title,
            description,
            body_part,
            size,
            reference_url,
            'pending',
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': 'Pedido de tatuagem enviado com sucesso.'}), 201


@app.route('/api/tattoos/approve', methods=['POST'])
@admin_required
def approve_tattoo():
    payload = request.get_json(silent=True) or {}
    customer_id = payload.get('customerId')
    if not customer_id:
        return jsonify({'error': 'customerId obrigatório.'}), 400

    conn = get_db()
    conn.execute(
        'INSERT INTO tattoo_sessions (customer_id, admin_name, status, approved_at, notes) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)',
        (customer_id, payload.get('adminName') or 'Admin', 'approved', 'Tatuagem aprovada pelo sistema.'),
    )

    current = conn.execute('SELECT * FROM loyalty_progress WHERE customer_id = %s', (customer_id,)).fetchone()
    completed = (current['completed_tattoos'] if current else 0) + 1
    milestones = completed // 3
    previous_milestone = current['last_milestone'] if current else 0
    new_spins = max(0, milestones - previous_milestone)

    if current:
        conn.execute(
            'UPDATE loyalty_progress SET completed_tattoos = %s, available_spins = available_spins + %s, last_milestone = %s, updated_at = CURRENT_TIMESTAMP WHERE customer_id = %s',
            (completed, new_spins, milestones, customer_id),
        )
    else:
        conn.execute(
            'INSERT INTO loyalty_progress (customer_id, completed_tattoos, available_spins, last_milestone, updated_at) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)',
            (customer_id, completed, new_spins, milestones),
        )

    spin_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    for _ in range(new_spins):
        conn.execute(
            'INSERT INTO customer_spins (customer_id, source, status, expires_at) '
            'VALUES (%s, %s, %s, %s)',
            (customer_id, 'loyalty', 'pending', spin_expires_at),
        )

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'completed': completed, 'newSpins': new_spins})


@app.route('/api/customers/<int:customer_id>/loyalty', methods=['GET'])
@customer_required
def get_loyalty(customer_id):
    if customer_id != session.get('customer_id'):
        return jsonify({'error': 'Sem autorização.'}), 403
    conn = get_db()
    loyalty = conn.execute('SELECT * FROM loyalty_progress WHERE customer_id = %s', (customer_id,)).fetchone()
    conn.close()
    if not loyalty:
        return jsonify({'loyalty': {'completed_tattoos': 0, 'available_spins': 0, 'last_milestone': 0}})
    return jsonify({'loyalty': dict(loyalty)})


@app.route('/')
def index():
    return send_from_directory(str(WEB_ROOT), 'index.html')


@app.route('/mvp')
@app.route('/mvp/')
def mvp_index():
    return redirect('/', code=302)


@app.route('/mvp-assets/<path:filename>')
def mvp_assets(filename):
    return send_from_directory(str(STATIC_DIR), filename)


@app.route('/<path:filename>')
def web_file(filename):
    if filename.startswith('assets/'):
        return send_from_directory(str(WEB_ROOT), filename)
    if filename not in {
        'styles.css', 'login.js', 'script.js', 'admin.js', 'njnaruto.ttf',
        'esqueci-senha.html', 'guia.html',
    }:
        abort(404)
    return send_from_directory(str(WEB_ROOT), filename)


def run_local():
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5000'))
    init_db()
    seed_prizes()
    browser_host = '127.0.0.1' if host in {'0.0.0.0', '::'} else host
    url = f'http://{browser_host}:{port}'
    print(f'Site iniciado em {url}. Feche esta janela para encerrar o servidor.')
    threading.Timer(1, webbrowser.open, args=(url,)).start()
    app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False,
    )


if __name__ == '__main__':
    run_local()
