// Interface remanescente do MVP antigo; a versão principal não carrega este arquivo.
// As rotas atuais redirecionam /mvp para a home, mas os recursos são mantidos
// para compatibilidade e referência histórica.
const API = '/api';

const registerForm = document.getElementById('registerForm');
const customerLoginForm = document.getElementById('customerLoginForm');
const customerLogoutBtn = document.getElementById('customerLogoutBtn');
const accountStatus = document.getElementById('accountStatus');
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
let currentRotation = 0;

async function fetchJson(url, options = {}) {
  // Wrapper HTTP usado pela interface antiga para enviar cookies e tratar erros JSON.
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const response = await fetch(url, { ...options, headers, credentials: 'same-origin' });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Não foi possível concluir a solicitação.');
  return result;
}

function showStatus(message, isError = false) {
  accountStatus.textContent = message;
  accountStatus.classList.toggle('error', isError);
}

function renderLoyaltyGrid(completed = 0) {
  // Desenha os nove marcadores visuais de progresso do cliente.
  const total = 9;
  const boxes = Array.from({ length: total }, (_, index) => index + 1);
  loyaltyGrid.innerHTML = boxes.map((item) => `
    <div class="loyalty-box ${item <= completed ? 'filled' : ''}">${item <= completed ? '✦' : '○'}</div>
  `).join('');
  loyaltyMeta.textContent = `${completed}/${total} caixinhas preenchidas`;
}

async function loadCustomerLoyalty() {
  // Consulta ao backend o total concluído e atualiza os marcadores.
  if (!currentCustomerId) return;
  const data = await fetchJson(`${API}/customers/${currentCustomerId}/loyalty`);
  renderLoyaltyGrid(Math.min(data.loyalty?.completed_tattoos || 0, 9));
}

function setCustomer(customer) {
  // Alterna os controles visíveis conforme a sessão de cliente recebida.
  currentCustomerId = customer?.id || null;
  customerLogoutBtn.classList.toggle('hidden', !currentCustomerId);
  registerForm.classList.toggle('hidden', Boolean(currentCustomerId));
  if (currentCustomerId) {
    showStatus(`Conectado(a) como ${customer.name || 'cliente'}.`);
    ideaForm.elements.customerId.value = currentCustomerId;
    loadCustomerLoyalty().catch((error) => showStatus(error.message, true));
  } else {
    ideaForm.elements.customerId.value = '';
  }
}

function setAdminVisibility(isLogged) {
  // Exibe login ou conteúdo administrativo na interface antiga do MVP.
  adminLoginForm.classList.toggle('hidden', isLogged);
  adminContent.classList.toggle('hidden', !isLogged);
}

registerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(registerForm).entries());
  try {
    const result = await fetchJson(`${API}/auth/register`, {
      method: 'POST',
      body: JSON.stringify(body)
    });
    showStatus(result.message);
    registerForm.reset();
  } catch (error) {
    showStatus(error.message, true);
  }
});

customerLoginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(customerLoginForm).entries());
  try {
    await fetchJson(`${API}/auth/login`, {
      method: 'POST',
      body: JSON.stringify(body)
    });
    const data = await fetchJson(`${API}/auth/me`);
    setCustomer(data.customer);
  } catch (error) {
    showStatus(error.message, true);
  }
});

customerLogoutBtn.addEventListener('click', async () => {
  try {
    await fetchJson(`${API}/auth/logout`, { method: 'POST' });
    setCustomer(null);
    showStatus('Você saiu da sua conta.');
  } catch (error) {
    showStatus(error.message, true);
  }
});

spinBtn.addEventListener('click', async () => {
  // O servidor sorteia o prêmio; este listener apenas anima e mostra o resultado.
  if (!currentCustomerId) {
    resultBox.textContent = 'Entre na sua conta antes de girar.';
    return;
  }
  try {
    const response = await fetchJson(`${API}/spins/roll`, {
      method: 'POST',
      body: JSON.stringify({})
    });
    const targetAngle = 330 - (response.result.segmentIndex * 60);
    const currentAngle = ((currentRotation % 360) + 360) % 360;
    currentRotation += 360 * 6 + ((targetAngle - currentAngle + 360) % 360);
    wheel.style.transform = `rotate(${currentRotation}deg)`;
    resultBox.textContent = `${response.result.prizeName} | ${response.result.discountPercent}% de desconto`;
    await loadCustomerLoyalty();
  } catch (error) {
    resultBox.textContent = error.message;
  }
});

ideaForm.addEventListener('submit', async (event) => {
  // Envia a ideia e eventual imagem de referência como formulário multipart.
  event.preventDefault();
  const formData = new FormData(ideaForm);
  formData.delete('customerId');
  try {
    const response = await fetch(`${API}/tattoos/request`, {
      method: 'POST',
      body: formData,
      credentials: 'same-origin'
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Não foi possível enviar a ideia.');
    alert(result.message || 'Ideia enviada com sucesso!');
    ideaForm.reset();
    ideaForm.elements.customerId.value = currentCustomerId || '';
  } catch (error) {
    alert(error.message);
  }
});

showAdminBtn.addEventListener('click', () => {
  adminPanel.classList.toggle('hidden');
});

adminLoginForm.addEventListener('submit', async (event) => {
  // Autentica o desenvolvedor na API e carrega os dados do painel antigo.
  event.preventDefault();
  const formData = new FormData(adminLoginForm);
  try {
    await fetchJson(`${API}/admin/login`, {
      method: 'POST',
      body: JSON.stringify({
        username: formData.get('username'),
        password: formData.get('password')
      })
    });
    setCustomer(null);
    setAdminVisibility(true);
    await loadAdminData();
  } catch (error) {
    alert(error.message);
  }
});

logoutAdminBtn.addEventListener('click', async () => {
  try {
    await fetchJson(`${API}/admin/logout`, { method: 'POST' });
    setAdminVisibility(false);
    adminTable.replaceChildren();
  } catch (error) {
    alert(error.message);
  }
});

function escapeHtml(value) {
  // Protege dados de texto ao montar linhas HTML da tabela antiga.
  return String(value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[character]);
}

async function loadAdminData() {
  // Carrega a lista para o administrador e liga ações de aprovação de tatuagem.
  try {
    const data = await fetchJson(`${API}/admin/customers`);
    if (!data.customers.length) {
      adminTable.textContent = 'Nenhum cliente cadastrado.';
      return;
    }

    const rows = data.customers.map((customer) => `
      <tr>
        <td>${customer.id}</td>
        <td>${escapeHtml(customer.name)}</td>
        <td>${escapeHtml(customer.whatsapp)}</td>
        <td><button data-customer-id="${customer.id}" class="approve-btn">Aprovar tatuagem</button></td>
      </tr>
    `).join('');

    adminTable.innerHTML = `
      <table>
        <thead><tr><th>ID</th><th>Nome</th><th>WhatsApp</th><th>Ação</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    adminTable.querySelectorAll('.approve-btn').forEach((button) => {
      button.addEventListener('click', async () => {
        try {
          const response = await fetchJson(`${API}/tattoos/approve`, {
            method: 'POST',
            body: JSON.stringify({ customerId: button.dataset.customerId, adminName: 'Admin' })
          });
          alert(`Tatuagem aprovada. Novas rodadas: ${response.newSpins}`);
          await loadAdminData();
        } catch (error) {
          alert(error.message);
        }
      });
    });
  } catch (error) {
    alert(error.message);
  }
}

loadAdminBtn.addEventListener('click', loadAdminData);

setAdminVisibility(false);
renderLoyaltyGrid(0);
fetchJson(`${API}/auth/me`)
  .then((data) => setCustomer(data.customer))
  .catch(() => setCustomer(null));
