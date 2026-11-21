"""Servidor local independente para demonstrar a roleta sem banco de dados."""
from datetime import datetime, timezone
from pathlib import Path
import secrets
import threading
import webbrowser

from flask import Flask, abort, jsonify, redirect, send_from_directory


PROJECT_ROOT = Path(__file__).resolve().parent
PORT = 5051
PUBLIC_FILES = {'styles.css', 'script.js', 'roleta.js', 'njnaruto.ttf'}
DEMO_PRIZES = (
    {'id': 1, 'name': '1 Tomoe', 'discount_percent': 5, 'tomoe_level': 1, 'probability_weight': 35},
    {'id': 2, 'name': '2 Tomoes', 'discount_percent': 10, 'tomoe_level': 2, 'probability_weight': 25},
    {'id': 3, 'name': '3 Tomoes', 'discount_percent': 15, 'tomoe_level': 3, 'probability_weight': 18},
    {'id': 4, 'name': 'Sharingan 1', 'discount_percent': 20, 'tomoe_level': 3, 'probability_weight': 12},
    {'id': 5, 'name': 'Sharingan 2', 'discount_percent': 30, 'tomoe_level': 3, 'probability_weight': 7},
    {'id': 6, 'name': 'Lenda', 'discount_percent': 40, 'tomoe_level': 3, 'probability_weight': 3},
)

app = Flask(__name__, static_folder=None)


@app.get('/')
def home():
    return redirect('/roleta.html')


@app.get('/roleta.html')
def roulette_page():
    return send_from_directory(PROJECT_ROOT, 'roleta.html')


@app.get('/assets/img/<path:filename>')
def public_image(filename):
    return send_from_directory(PROJECT_ROOT / 'assets' / 'img', filename)


@app.get('/<path:filename>')
def public_file(filename):
    if filename not in PUBLIC_FILES:
        abort(404)
    return send_from_directory(PROJECT_ROOT, filename)


@app.get('/api/prizes')
def demo_prizes():
    return jsonify({'prizes': [dict(prize) for prize in DEMO_PRIZES]})


@app.post('/api/spins/preview')
def preview_spin():
    total_weight = sum(prize['probability_weight'] for prize in DEMO_PRIZES)
    ticket = secrets.randbelow(total_weight) + 1
    cumulative_weight = 0

    for segment_index, prize in enumerate(DEMO_PRIZES):
        cumulative_weight += prize['probability_weight']
        if ticket <= cumulative_weight:
            result = {
                'prizeId': prize['id'],
                'segmentIndex': segment_index,
                'prizeName': prize['name'],
                'discountPercent': float(prize['discount_percent']),
                'tomoeLevel': prize['tomoe_level'],
                'rolledAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            }
            return jsonify({'ok': True, 'preview': True, 'result': result})

    raise RuntimeError('No demo prize matched the generated ticket.')


if __name__ == '__main__':
    url = f'http://127.0.0.1:{PORT}/roleta.html'
    print(f'Opening the demo roulette at {url}')
    threading.Timer(1, webbrowser.open_new_tab, args=(url,)).start()
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)
