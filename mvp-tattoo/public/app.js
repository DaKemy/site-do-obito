const API = 'http://localhost:5000/api';

const registerForm = document.getElementById('registerForm');
const spinBtn = document.getElementById('spinBtn');
const wheel = document.getElementById('wheel');
const resultBox = document.getElementById('resultBox');
const loyaltyGrid = document.getElementById('loyaltyGrid');
const loyaltyMeta = document.getElementById('loyaltyMeta');
const ideaForm = document.getElementById('ideaForm');
const adminPanel = document.getElementById('adminPanel');
const showAdminBtn = document.getElementById('showAdminBtn');
const loadAdminBtn = document.getElementById('loadAdminBtn');
const adminTable = document.getElementById('adminTable');
const adminLoginForm = document.getElementById('adminLoginForm');
const adminContent = document.getElementById('adminContent');
const logoutAdminBtn = document.getElementById('logoutAdminBtn');

let currentCustomerId = null;

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

function renderLoyaltyGrid(completed = 0) {
  const total = 9;
  const boxes = Array.from({ length: total }, (_, index) => index + 1);

  loyaltyGrid.innerHTML = boxes.map((item) => `
    <div class="loyalty-box ${item <= completed ? 'filled' : ''}">${item <= completed ? '✦' : '○'}</div>
  `).join('');

  loyaltyMeta.textContent = `${completed}/${total} caixinhas preenchidas`;
}

async function loadCustomerLoyalty() {
  if (!currentCustomerId) return;
  const data = await fetchJson(`${API}/customers/${currentCustomerId}/loyalty`);
  const completed = data.loyalty?.completed_tattoos || 0;
  renderLoyaltyGrid(Math.min(completed, 9));
}

function setAdminVisibility(isLogged) {
  const loginForm = document.getElementById('adminLoginForm');
  const adminContentBlock = document.getElementById('adminContent');
  if (loginForm) loginForm.classList.toggle('hidden', isLogged);
  if (adminContentBlock) adminContentBlock.classList.toggle('hidden', !isLogged);
}

registerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(registerForm);
  const body = {
    whatsapp: formData.get('whatsapp'),
    name: formData.get('name')
  };

  const result = await fetchJson(`${API}/customers/register`, {
    method: 'POST',
    body: JSON.stringify(body)
  });

  if (result.customer) {
    currentCustomerId = result.customer.id;
    resultBox.textContent = `Cliente registrado: ${result.customer.name}`;
    document.querySelector('input[name="customerId"]').value = currentCustomerId;
    await loadCustomerLoyalty();
  }
});

spinBtn.addEventListener('click', async () => {
  if (!currentCustomerId) {
    resultBox.textContent = 'Cadastre um cliente antes de girar.';
    return;
  }

  const response = await fetchJson(`${API}/spins/roll`, {
    method: 'POST',
    body: JSON.stringify({ customerId: currentCustomerId })
  });

  if (response.error) {
    resultBox.textContent = response.error;
    return;
  }

  const rotation = 360 * 6 + (360 - (response.result.tomoeLevel * 60));
  wheel.style.transform = `rotate(${rotation}deg)`;
  resultBox.textContent = `${response.result.prizeName} | ${response.result.discountPercent}% de desconto`;
  await loadCustomerLoyalty();
});

ideaForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(ideaForm);

  const response = await fetch(`${API}/tattoos/request`, {
    method: 'POST',
    body: formData
  });

  const result = await response.json();
  alert(result.message || 'Ideia enviada com sucesso!');
  ideaForm.reset();
});

showAdminBtn.addEventListener('click', () => {
  adminPanel.classList.toggle('hidden');
});

adminLoginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(adminLoginForm);
  const response = await fetchJson(`${API}/admin/login`, {
    method: 'POST',
    body: JSON.stringify({
      username: formData.get('username'),
      password: formData.get('password')
    })
  });

  if (response.ok) {
    setAdminVisibility(true);
    await loadAdminData();
    return;
  }

  alert(response.error || 'Erro ao entrar.');
});

logoutAdminBtn.addEventListener('click', async () => {
  await fetchJson(`${API}/admin/logout`, { method: 'POST' });
  setAdminVisibility(false);
  adminTable.innerHTML = '';
});

async function loadAdminData() {
  const data = await fetchJson(`${API}/admin/customers`);
  if (data.error) {
    alert(data.error);
    return;
  }

  if (!data.customers || !data.customers.length) {
    adminTable.innerHTML = '<p>Nenhum cliente cadastrado.</p>';
    return;
  }

  const rows = data.customers.map((customer) => `
    <tr>
      <td>${customer.id}</td>
      <td>${customer.name}</td>
      <td>${customer.whatsapp}</td>
      <td>
        <button data-customer-id="${customer.id}" class="approve-btn">Aprovar tatuagem</button>
      </td>
    </tr>
  `).join('');

  adminTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Nome</th>
          <th>WhatsApp</th>
          <th>Ação</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;

  document.querySelectorAll('.approve-btn').forEach((button) => {
    button.addEventListener('click', async () => {
      const customerId = button.dataset.customerId;
      const response = await fetchJson(`${API}/tattoos/approve`, {
        method: 'POST',
        body: JSON.stringify({ customerId, adminName: 'Admin' })
      });

      alert(`Tatuagem aprovada. Novas rodadas: ${response.newSpins || 0}`);
      await loadCustomerLoyalty();
      await loadAdminData();
    });
  });
}

loadAdminBtn.addEventListener('click', async () => {
  const adminCheck = await fetchJson(`${API}/admin/me`);
  if (adminCheck.error) {
    alert('Faça login antes de acessar o painel administrativo.');
    setAdminVisibility(false);
    return;
  }
  await loadAdminData();
});

setAdminVisibility(false);
renderLoyaltyGrid(0);
