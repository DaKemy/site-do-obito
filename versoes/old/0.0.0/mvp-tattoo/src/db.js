const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const dbPath = path.join(__dirname, '..', 'data.sqlite');
const db = new sqlite3.Database(dbPath);

function run(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function (err) {
      if (err) return reject(err);
      resolve({ id: this.lastID, changes: this.changes });
    });
  });
}

function get(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) return reject(err);
      resolve(row);
    });
  });
}

function all(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) return reject(err);
      resolve(rows);
    });
  });
}

function initDatabase() {
  const schema = `
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
  `;

  return new Promise((resolve, reject) => {
    db.exec(schema, (err) => {
      if (err) return reject(err);
      resolve();
    });
  });
}

async function seedPrizes() {
  const prizes = [
    { name: '1 Tomoe', discount_percent: 5, tomoe_level: 1, probability_weight: 35 },
    { name: '2 Tomoes', discount_percent: 10, tomoe_level: 2, probability_weight: 25 },
    { name: '3 Tomoes', discount_percent: 15, tomoe_level: 3, probability_weight: 18 },
    { name: 'Sharingan 1', discount_percent: 20, tomoe_level: 3, probability_weight: 12 },
    { name: 'Sharingan 2', discount_percent: 30, tomoe_level: 3, probability_weight: 7 },
    { name: 'Lenda', discount_percent: 40, tomoe_level: 3, probability_weight: 3 },
  ];

  const existing = await all('SELECT COUNT(*) AS total FROM reward_prizes');
  if (existing[0].total > 0) return;

  for (const prize of prizes) {
    await run(
      'INSERT INTO reward_prizes (name, discount_percent, tomoe_level, probability_weight, active) VALUES (?, ?, ?, ?, 1)',
      [prize.name, prize.discount_percent, prize.tomoe_level, prize.probability_weight]
    );
  }
}

module.exports = { db, run, get, all, initDatabase, seedPrizes };
