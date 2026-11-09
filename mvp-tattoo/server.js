const express = require('express');
const cors = require('cors');
const crypto = require('crypto');
const path = require('path');
const { db, run, get, all, initDatabase, seedPrizes } = require('./src/db');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

function pickWeightedPrize() {
  return new Promise(async (resolve, reject) => {
    try {
      const prizes = await all('SELECT * FROM reward_prizes WHERE active = 1');
      const totalWeight = prizes.reduce((sum, item) => sum + item.probability_weight, 0);
      const randomValue = crypto.randomInt(1, totalWeight + 1);

      let cursor = 0;
      for (const prize of prizes) {
        cursor += prize.probability_weight;
        if (randomValue <= cursor) {
          return resolve(prize);
        }
      }

      resolve(prizes[0]);
    } catch (err) {
      reject(err);
    }
  });
}

function buildCustomerSummary(customer) {
  return {
    id: customer.id,
    whatsapp: customer.whatsapp,
    name: customer.name,
    created_at: customer.created_at
  };
}

app.get('/api/health', (req, res) => {
  res.json({ ok: true, message: 'Tattoo MVP online' });
});

app.post('/api/customers/register', async (req, res) => {
  try {
    const { whatsapp, name } = req.body || {};
    if (!whatsapp || !name) {
      return res.status(400).json({ error: 'WhatsApp e nome são obrigatórios.' });
    }

    const sanitizedWhatsapp = String(whatsapp).trim();
    const sanitizedName = String(name).trim();

    if (!sanitizedWhatsapp || !sanitizedName) {
      return res.status(400).json({ error: 'Dados inválidos.' });
    }

    const existing = await get('SELECT * FROM customers WHERE whatsapp = ?', [sanitizedWhatsapp]);
    if (existing) {
      return res.status(200).json({
        ok: true,
        customer: buildCustomerSummary(existing),
        message: 'Cliente já cadastrado.'
      });
    }

    const customerResult = await run('INSERT INTO customers (whatsapp, name) VALUES (?, ?)', [sanitizedWhatsapp, sanitizedName]);
    const customer = await get('SELECT * FROM customers WHERE id = ?', [customerResult.id]);

    await run('INSERT INTO customer_spins (customer_id, source, status, expires_at) VALUES (?, ?, ?, datetime("now", "+30 days"))', [customer.id, 'signup', 'pending']);

    const loyalty = await get('SELECT * FROM loyalty_progress WHERE customer_id = ?', [customer.id]);
    if (!loyalty) {
      await run('INSERT INTO loyalty_progress (customer_id, completed_tattoos, available_spins, last_milestone) VALUES (?, 0, 0, 0)', [customer.id]);
    }

    return res.status(201).json({ ok: true, customer: buildCustomerSummary(customer) });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Erro ao registrar cliente.' });
  }
});

app.get('/api/customers/:id', async (req, res) => {
  try {
    const customer = await get('SELECT * FROM customers WHERE id = ?', [req.params.id]);
    if (!customer) {
      return res.status(404).json({ error: 'Cliente não encontrado.' });
    }

    const spins = await all('SELECT * FROM customer_spins WHERE customer_id = ? ORDER BY rolled_at DESC', [customer.id]);
    const requests = await all('SELECT * FROM tattoo_requests WHERE customer_id = ? ORDER BY created_at DESC', [customer.id]);
    const loyalty = await get('SELECT * FROM loyalty_progress WHERE customer_id = ?', [customer.id]);

    return res.json({ customer: buildCustomerSummary(customer), spins, requests, loyalty });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Erro ao buscar cliente.' });
  }
});

app.post('/api/spins/roll', async (req, res) => {
  try {
    const { customerId } = req.body || {};
    if (!customerId) {
      return res.status(400).json({ error: 'customerId obrigatório.' });
    }

    const customer = await get('SELECT * FROM customers WHERE id = ?', [customerId]);
    if (!customer) {
      return res.status(404).json({ error: 'Cliente não encontrado.' });
    }

    const pendingSpin = await get('SELECT * FROM customer_spins WHERE customer_id = ? AND status = ? ORDER BY rolled_at ASC LIMIT 1', [customerId, 'pending']);
    if (!pendingSpin) {
      return res.status(400).json({ error: 'Nenhuma rodada disponível.' });
    }

    const prize = await pickWeightedPrize();
    const result = {
      prizeId: prize.id,
      prizeName: prize.name,
      discountPercent: Number(prize.discount_percent),
      tomoeLevel: prize.tomoe_level,
      rolledAt: new Date().toISOString()
    };

    const randomSeed = crypto.randomUUID();
    const couponCode = `TAT-${Date.now().toString().slice(-6)}`;
    const expiresAt = new Date(Date.now() + 1000 * 60 * 60 * 24 * 30).toISOString();

    await run(
      'UPDATE customer_spins SET prize_id = ?, status = ?, used_at = CURRENT_TIMESTAMP, expires_at = ?, random_seed = ?, server_result = ? WHERE id = ?',
      [prize.id, 'used', expiresAt, randomSeed, JSON.stringify(result), pendingSpin.id]
    );

    const coupon = await run(
      'INSERT INTO coupons (customer_id, spin_id, code, discount_percent, status, expires_at) VALUES (?, ?, ?, ?, ?, ?)',
      [customerId, pendingSpin.id, couponCode, result.discountPercent, 'active', expiresAt]
    );

    return res.status(200).json({
      ok: true,
      result,
      coupon: {
        id: coupon.id,
        code: couponCode,
        discountPercent: Number(result.discountPercent),
        expiresAt
      }
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Erro ao sortear prêmio.' });
  }
});

app.get('/api/admin/customers', async (req, res) => {
  try {
    const customers = await all('SELECT * FROM customers ORDER BY created_at DESC');
    const allSessions = await all('SELECT * FROM tattoo_sessions ORDER BY created_at DESC');
    const allRequests = await all('SELECT * FROM tattoo_requests ORDER BY created_at DESC');
    return res.json({ customers, sessions: allSessions, requests: allRequests });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Erro ao listar clientes.' });
  }
});

app.post('/api/tattoos/request', async (req, res) => {
  try {
    const { customerId, title, description, bodyPart, size, referenceImageUrl } = req.body || {};
    if (!customerId || !description) {
      return res.status(400).json({ error: 'customerId e descrição são obrigatórios.' });
    }

    const result = await run(
      'INSERT INTO tattoo_requests (customer_id, title, description, body_part, size, reference_image_url, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
      [customerId, title || 'Ideia de tatuagem', description, bodyPart || '', size || '', referenceImageUrl || '', 'pending']
    );

    return res.status(201).json({ ok: true, id: result.id, message: 'Pedido de tatuagem enviado.' });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Erro ao enviar ideia.' });
  }
});

app.post('/api/tattoos/approve', async (req, res) => {
  try {
    const { customerId, adminName } = req.body || {};
    if (!customerId) {
      return res.status(400).json({ error: 'customerId obrigatório.' });
    }

    const session = await run(
      'INSERT INTO tattoo_sessions (customer_id, admin_name, status, approved_at, notes) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)',
      [customerId, adminName || 'Admin', 'approved', 'Tatuagem aprovada pelo sistema.']
    );

    const currentTotal = await get('SELECT completed_tattoos FROM loyalty_progress WHERE customer_id = ?', [customerId]);
    const completed = (currentTotal?.completed_tattoos || 0) + 1;
    const milestones = Math.floor(completed / 3);
    const previousMilestones = Number((await get('SELECT last_milestone FROM loyalty_progress WHERE customer_id = ?', [customerId]))?.last_milestone || 0);
    const newSpins = Math.max(0, milestones - previousMilestones);

    await run(
      'INSERT INTO loyalty_progress (customer_id, completed_tattoos, available_spins, last_milestone, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP) ON CONFLICT(customer_id) DO UPDATE SET completed_tattoos = excluded.completed_tattoos, available_spins = available_spins + excluded.available_spins, last_milestone = excluded.last_milestone, updated_at = CURRENT_TIMESTAMP',
      [customerId, completed, newSpins, milestones]
    );

    for (let i = 0; i < newSpins; i++) {
      await run('INSERT INTO customer_spins (customer_id, source, status, expires_at) VALUES (?, ?, ?, datetime("now", "+30 days"))', [customerId, 'loyalty', 'pending']);
    }

    return res.status(200).json({ ok: true, sessionId: session.id, completed, newSpins });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Erro ao aprovar tatuagem.' });
  }
});

app.get('/api/customers/:id/loyalty', async (req, res) => {
  try {
    const loyalty = await get('SELECT * FROM loyalty_progress WHERE customer_id = ?', [req.params.id]);
    return res.json({ loyalty: loyalty || { completed_tattoos: 0, available_spins: 0, last_milestone: 0 } });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Erro ao consultar fidelidade.' });
  }
});

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

async function startServer() {
  await initDatabase();
  await seedPrizes();

  app.listen(PORT, () => {
    console.log(`MVP rodando em http://localhost:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Falha ao iniciar:', err);
  process.exit(1);
});
