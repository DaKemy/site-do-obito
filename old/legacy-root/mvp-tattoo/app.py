from __future__ import annotations

import json
import os
import secrets
import threading
import traceback
import uuid
import webbrowser
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import sqlite3
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / '.env')
DB_PATH = BASE_DIR / 'data.sqlite'
STATIC_DIR = BASE_DIR / 'public'
UPLOAD_FOLDER = BASE_DIR / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path='')
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

if not app.secret_key or not ADMIN_USERNAME or not ADMIN_PASSWORD:
    raise RuntimeError(
        'Set FLASK_SECRET_KEY, ADMIN_USERNAME, and ADMIN_PASSWORD environment variables.'
    )


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({'error': 'Sem autorização de administrador.'}), 401
        return view(*args, **kwargs)
    return wrapped


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whatsapp TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reward_prizes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            discount_percent REAL NOT NULL,
            tomoe_level INTEGER NOT NULL,
            probability_weight INTEGER NOT NULL,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS customer_spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            prize_id INTEGER,
            source TEXT NOT NULL DEFAULT 'signup',
            status TEXT NOT NULL DEFAULT 'pending',
            rolled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            used_at DATETIME,
            expires_at DATETIME,
            random_seed TEXT,
            server_result TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        );

        CREATE TABLE IF NOT EXISTS tattoo_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            admin_name TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            approved_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        );

        CREATE TABLE IF NOT EXISTS loyalty_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER UNIQUE NOT NULL,
            completed_tattoos INTEGER DEFAULT 0,
            available_spins INTEGER DEFAULT 0,
            last_milestone INTEGER DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        );

        CREATE TABLE IF NOT EXISTS tattoo_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            title TEXT,
            description TEXT NOT NULL,
            body_part TEXT,
            size TEXT,
            reference_image_url TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        );

        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            spin_id INTEGER,
            code TEXT UNIQUE NOT NULL,
            discount_percent REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            expires_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(spin_id) REFERENCES customer_spins(id)
        );
        """
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
        'INSERT INTO reward_prizes (name, discount_percent, tomoe_level, probability_weight, active) VALUES (?, ?, ?, ?, 1)',
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
    prizes = conn.execute('SELECT * FROM reward_prizes WHERE active = 1').fetchall()
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
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/health')
def health():
    return jsonify({'ok': True, 'message': 'Tattoo MVP online'})


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip()
    password = (payload.get('password') or '').strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        session['admin_user'] = username
        return jsonify({'ok': True, 'user': username})

    return jsonify({'error': 'Credenciais inválidas.'}), 401


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/admin/me', methods=['GET'])
def admin_me():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Não autenticado.'}), 401
    return jsonify({'ok': True, 'user': session.get('admin_user')})


@app.route('/api/customers/register', methods=['POST'])
def register_customer():
    payload = request.get_json(silent=True) or {}
    whatsapp = (payload.get('whatsapp') or '').strip()
    name = (payload.get('name') or '').strip()

    if not whatsapp or not name:
        return jsonify({'error': 'WhatsApp e nome são obrigatórios.'}), 400

    conn = get_db()
    existing = conn.execute('SELECT * FROM customers WHERE whatsapp = ?', (whatsapp,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'ok': True, 'customer': customer_summary(existing), 'message': 'Cliente já cadastrado.'})

    cursor = conn.execute(
        'INSERT INTO customers (whatsapp, name) VALUES (?, ?)',
        (whatsapp, name),
    )
    customer_id = cursor.lastrowid
    conn.execute(
        'INSERT INTO customer_spins (customer_id, source, status, expires_at) VALUES (?, ?, ?, datetime("now", "+30 days"))',
        (customer_id, 'signup', 'pending'),
    )
    existing_loyalty = conn.execute('SELECT * FROM loyalty_progress WHERE customer_id = ?', (customer_id,)).fetchone()
    if existing_loyalty is None:
        conn.execute(
            'INSERT INTO loyalty_progress (customer_id, completed_tattoos, available_spins, last_milestone) VALUES (?, 0, 0, 0)',
            (customer_id,),
        )
    conn.commit()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    conn.close()
    return jsonify({'ok': True, 'customer': customer_summary(customer)}), 201


@app.route('/api/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return jsonify({'error': 'Cliente não encontrado.'}), 404

    spins = conn.execute(
        'SELECT * FROM customer_spins WHERE customer_id = ? ORDER BY rolled_at DESC',
        (customer_id,),
    ).fetchall()
    requests = conn.execute(
        'SELECT * FROM tattoo_requests WHERE customer_id = ? ORDER BY created_at DESC',
        (customer_id,),
    ).fetchall()
    loyalty = conn.execute('SELECT * FROM loyalty_progress WHERE customer_id = ?', (customer_id,)).fetchone()
    conn.close()
    return jsonify({
        'customer': customer_summary(customer),
        'spins': [dict(row) for row in spins],
        'requests': [dict(row) for row in requests],
        'loyalty': dict(loyalty) if loyalty else {'completed_tattoos': 0, 'available_spins': 0, 'last_milestone': 0},
    })


@app.route('/api/spins/roll', methods=['POST'])
def roll_spin():
    payload = request.get_json(silent=True) or {}
    customer_id = payload.get('customerId')
    if not customer_id:
        return jsonify({'error': 'customerId obrigatório.'}), 400

    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return jsonify({'error': 'Cliente não encontrado.'}), 404

    pending_spin = conn.execute(
        'SELECT * FROM customer_spins WHERE customer_id = ? AND status = ? ORDER BY rolled_at ASC LIMIT 1',
        (customer_id, 'pending'),
    ).fetchone()
    if not pending_spin:
        conn.close()
        return jsonify({'error': 'Nenhuma rodada disponível.'}), 400

    prize = pick_weighted_prize()
    result = {
        'prizeId': prize['id'],
        'prizeName': prize['name'],
        'discountPercent': float(prize['discount_percent']),
        'tomoeLevel': int(prize['tomoe_level']),
        'rolledAt': datetime.utcnow().isoformat() + 'Z'
    }
    expires_at = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    random_seed = str(uuid.uuid4())
    coupon_code = f"TAT-{int(datetime.utcnow().timestamp() * 1000) % 1000000:06d}"

    conn.execute(
        'UPDATE customer_spins SET prize_id = ?, status = ?, used_at = CURRENT_TIMESTAMP, expires_at = ?, random_seed = ?, server_result = ? WHERE id = ?',
        (prize['id'], 'used', expires_at, random_seed, json.dumps(result), pending_spin['id']),
    )
    conn.execute(
        'INSERT INTO coupons (customer_id, spin_id, code, discount_percent, status, expires_at) VALUES (?, ?, ?, ?, ?, ?)',
        (customer_id, pending_spin['id'], coupon_code, result['discountPercent'], 'active', expires_at),
    )
    conn.commit()
    conn.close()

    return jsonify({'ok': True, 'result': result, 'coupon': {'code': coupon_code, 'discountPercent': result['discountPercent'], 'expiresAt': expires_at}})


@app.route('/api/admin/customers', methods=['GET'])
@admin_required
def admin_customers():
    conn = get_db()
    customers = conn.execute('SELECT * FROM customers ORDER BY created_at DESC').fetchall()
    sessions = conn.execute('SELECT * FROM tattoo_sessions ORDER BY created_at DESC').fetchall()
    requests = conn.execute('SELECT * FROM tattoo_requests ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify({'customers': [dict(row) for row in customers], 'sessions': [dict(row) for row in sessions], 'requests': [dict(row) for row in requests]})


@app.route('/api/tattoos/request', methods=['POST'])
def create_tattoo_request():
    customer_id = None
    description = ''
    payload = request.get_json(silent=True) or {}
    if request.files:
        file = request.files.get('referenceImage')
        customer_id = request.form.get('customerId')
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
        customer_id = payload.get('customerId')
        description = (payload.get('description') or '').strip()
        title = payload.get('title') or 'Ideia de tatuagem'
        body_part = payload.get('bodyPart') or ''
        size = payload.get('size') or ''
        reference_url = payload.get('referenceImageUrl') or ''

    if not customer_id or not description:
        return jsonify({'error': 'customerId e descrição são obrigatórios.'}), 400

    conn = get_db()
    conn.execute(
        'INSERT INTO tattoo_requests (customer_id, title, description, body_part, size, reference_image_url, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
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
        'INSERT INTO tattoo_sessions (customer_id, admin_name, status, approved_at, notes) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)',
        (customer_id, payload.get('adminName') or 'Admin', 'approved', 'Tatuagem aprovada pelo sistema.'),
    )

    current = conn.execute('SELECT * FROM loyalty_progress WHERE customer_id = ?', (customer_id,)).fetchone()
    completed = (current['completed_tattoos'] if current else 0) + 1
    milestones = completed // 3
    previous_milestone = current['last_milestone'] if current else 0
    new_spins = max(0, milestones - previous_milestone)

    if current:
        conn.execute(
            'UPDATE loyalty_progress SET completed_tattoos = ?, available_spins = available_spins + ?, last_milestone = ?, updated_at = CURRENT_TIMESTAMP WHERE customer_id = ?',
            (completed, new_spins, milestones, customer_id),
        )
    else:
        conn.execute(
            'INSERT INTO loyalty_progress (customer_id, completed_tattoos, available_spins, last_milestone, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)',
            (customer_id, completed, new_spins, milestones),
        )

    for _ in range(new_spins):
        conn.execute(
            'INSERT INTO customer_spins (customer_id, source, status, expires_at) VALUES (?, ?, ?, datetime("now", "+30 days"))',
            (customer_id, 'loyalty', 'pending'),
        )

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'completed': completed, 'newSpins': new_spins})


@app.route('/api/customers/<int:customer_id>/loyalty', methods=['GET'])
def get_loyalty(customer_id):
    conn = get_db()
    loyalty = conn.execute('SELECT * FROM loyalty_progress WHERE customer_id = ?', (customer_id,)).fetchone()
    conn.close()
    if not loyalty:
        return jsonify({'loyalty': {'completed_tattoos': 0, 'available_spins': 0, 'last_milestone': 0}})
    return jsonify({'loyalty': dict(loyalty)})


@app.route('/')
def index():
    return send_from_directory(str(STATIC_DIR), 'index.html')


def run_local():
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5000'))
    init_db()
    seed_prizes()
    url = f'http://127.0.0.1:{port}'
    print(f'Site iniciado em {url}. Feche esta janela para encerrar o servidor.')
    threading.Timer(1, webbrowser.open, args=(url,)).start()
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    try:
        run_local()
    except Exception:
        traceback.print_exc()
        input('O site nao conseguiu iniciar. Pressione Enter para fechar esta janela...')
        raise
