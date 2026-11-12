const adminSection = document.getElementById('administracao');
const adminLoginView = document.getElementById('adminLoginView');
const adminLoginForm = document.getElementById('adminLoginForm');
const adminContent = document.getElementById('adminContent');
const adminMessage = document.getElementById('adminMessage');
const customerList = document.getElementById('adminCustomers');
const prizeList = document.getElementById('adminPrizes');
let customers = [];

async function adminRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            ...(options.body ? { 'Content-Type': 'application/json' } : {}),
            ...options.headers
        }
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Não foi possível concluir a operação.');
    return result;
}

function showAdminMessage(message, isError = false) {
    adminMessage.textContent = message;
    adminMessage.classList.toggle('error', isError);
}

function makeInput(labelText, name, value, type = 'text') {
    const label = document.createElement('label');
    label.textContent = labelText;
    const input = document.createElement('input');
    input.name = name;
    input.type = type;
    input.value = value ?? '';
    input.required = true;
    label.append(input);
    return { label, input };
}

function buildCustomerCard(customer) {
    const card = document.createElement('article');
    card.className = 'admin-customer-card';

    const heading = document.createElement('div');
    heading.className = 'admin-customer-heading';
    const title = document.createElement('h4');
    title.textContent = customer.name;
    const status = document.createElement('span');
    status.className = customer.email_verified ? 'admin-status verified' : 'admin-status';
    status.textContent = customer.email_verified ? 'E-mail confirmado' : 'E-mail pendente';
    heading.append(title, status);

    const details = document.createElement('p');
    details.className = 'admin-customer-details';
    details.textContent = `ID ${customer.id} · ${customer.email || 'Sem e-mail'} · ${customer.whatsapp}`;
    card.append(heading, details);

    const edit = document.createElement('details');
    edit.className = 'admin-details';
    const editSummary = document.createElement('summary');
    editSummary.textContent = 'Editar dados';
    const editForm = document.createElement('form');
    editForm.className = 'admin-form admin-edit-form';
    const nameField = makeInput('Nome', 'name', customer.name);
    const emailField = makeInput('E-mail', 'email', customer.email, 'email');
    emailField.input.required = false;
    const phoneField = makeInput('Telefone com DDD', 'whatsapp', customer.whatsapp, 'tel');
    editForm.append(nameField.label, emailField.label, phoneField.label);
    const saveButton = document.createElement('button');
    saveButton.className = 'btn btn-primary';
    saveButton.type = 'submit';
    saveButton.textContent = 'Salvar dados';
    editForm.append(saveButton);
    editForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        try {
            const result = await adminRequest(`/api/admin/customers/${customer.id}`, {
                method: 'PUT',
                body: JSON.stringify({
                    name: nameField.input.value,
                    email: emailField.input.value,
                    whatsapp: phoneField.input.value
                })
            });
            showAdminMessage(result.message);
            await loadCustomers();
        } catch (error) {
            showAdminMessage(error.message, true);
        }
    });
    edit.append(editSummary, editForm);
    card.append(edit);

    const reset = document.createElement('details');
    reset.className = 'admin-details';
    const resetSummary = document.createElement('summary');
    resetSummary.textContent = 'Redefinir senha';
    const resetForm = document.createElement('form');
    resetForm.className = 'admin-form admin-reset-form';
    const passwordField = makeInput('Nova senha (mínimo 8 caracteres)', 'password', '', 'password');
    passwordField.input.minLength = 8;
    passwordField.input.maxLength = 128;
    resetForm.append(passwordField.label);
    const resetButton = document.createElement('button');
    resetButton.className = 'btn btn-secondary';
    resetButton.type = 'submit';
    resetButton.textContent = 'Definir nova senha';
    resetForm.append(resetButton);
    resetForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!window.confirm(`Redefinir a senha de ${customer.name}?`)) return;
        try {
            const result = await adminRequest(`/api/admin/customers/${customer.id}/password`, {
                method: 'PUT',
                body: JSON.stringify({ password: passwordField.input.value })
            });
            passwordField.input.value = '';
            showAdminMessage(result.message);
            reset.open = false;
        } catch (error) {
            showAdminMessage(error.message, true);
        }
    });
    reset.append(resetSummary, resetForm);
    card.append(reset);

    const deleteButton = document.createElement('button');
    deleteButton.className = 'btn admin-delete-button';
    deleteButton.type = 'button';
    deleteButton.textContent = 'Excluir usuário';
    deleteButton.addEventListener('click', async () => {
        if (!window.confirm(`Excluir ${customer.name} e os dados associados a esta conta? Esta ação não pode ser desfeita.`)) return;
        try {
            const result = await adminRequest(`/api/admin/customers/${customer.id}`, { method: 'DELETE' });
            showAdminMessage(result.message);
            await loadCustomers();
        } catch (error) {
            showAdminMessage(error.message, true);
        }
    });
    card.append(deleteButton);
    return card;
}

function renderCustomers() {
    const query = document.getElementById('adminCustomerSearch').value.trim().toLowerCase();
    customerList.replaceChildren();
    const filtered = customers.filter((customer) =>
        [customer.name, customer.email, customer.whatsapp, String(customer.id)]
            .some((value) => String(value || '').toLowerCase().includes(query))
    );
    if (!filtered.length) {
        const empty = document.createElement('p');
        empty.className = 'admin-empty';
        empty.textContent = customers.length ? 'Nenhum usuário corresponde à busca.' : 'Ainda não há usuários cadastrados.';
        customerList.append(empty);
        return;
    }
    filtered.forEach((customer) => customerList.append(buildCustomerCard(customer)));
}

async function loadCustomers() {
    const result = await adminRequest('/api/admin/customers');
    customers = result.customers;
    renderCustomers();
}

async function loadPrizes() {
    const result = await adminRequest('/api/admin/prizes');
    prizeList.replaceChildren();
    result.prizes.forEach((prize) => {
        const row = document.createElement('div');
        row.className = 'admin-prize-row';
        row.dataset.prizeId = prize.id;

        const name = makeInput('Prêmio', 'name', prize.name);
        const discount = makeInput('Desconto (%)', 'discountPercent', prize.discount_percent, 'number');
        discount.input.min = 0.01;
        discount.input.max = 100;
        discount.input.step = 0.01;
        const tomoe = makeInput('Nível de tomoe', 'tomoeLevel', prize.tomoe_level, 'number');
        tomoe.input.min = 1;
        tomoe.input.max = 3;
        tomoe.input.step = 1;
        const weight = makeInput('Peso da chance', 'probabilityWeight', prize.probability_weight, 'number');
        weight.input.min = 1;
        weight.input.max = 10000;
        weight.input.step = 1;
        const activeLabel = document.createElement('label');
        activeLabel.className = 'admin-prize-active';
        const active = document.createElement('input');
        active.type = 'checkbox';
        active.name = 'active';
        active.checked = Boolean(prize.active);
        activeLabel.append(active, document.createTextNode('Prêmio ativo'));
        row.append(name.label, discount.label, tomoe.label, weight.label, activeLabel);
        prizeList.append(row);
    });
}

function setAdminAuthenticated(user) {
    adminLoginView.hidden = Boolean(user);
    adminContent.hidden = !user;
    document.getElementById('adminWelcome').textContent = user ? `Conectado como ${user}.` : '';
    if (user) {
        Promise.all([loadCustomers(), loadPrizes()])
            .then(() => showAdminMessage('Painel carregado.'))
            .catch((error) => showAdminMessage(error.message, true));
    }
}

async function openAdminPanel() {
    adminSection.hidden = false;
    try {
        const result = await adminRequest('/api/admin/me');
        setAdminAuthenticated(result.user);
    } catch (error) {
        setAdminAuthenticated(null);
    }
}

document.getElementById('adminOpenLink').addEventListener('click', openAdminPanel);

adminLoginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(adminLoginForm);
    try {
        const result = await adminRequest('/api/admin/login', {
            method: 'POST',
            body: JSON.stringify({
                username: formData.get('username'),
                password: formData.get('password')
            })
        });
        adminLoginForm.reset();
        setAdminAuthenticated(result.user);
    } catch (error) {
        showAdminMessage(error.message, true);
    }
});

document.getElementById('adminLogout').addEventListener('click', async () => {
    try {
        await adminRequest('/api/admin/logout', { method: 'POST' });
        setAdminAuthenticated(null);
        showAdminMessage('Sessão administrativa encerrada.');
    } catch (error) {
        showAdminMessage(error.message, true);
    }
});

document.querySelectorAll('[data-admin-tab]').forEach((button) => {
    button.addEventListener('click', () => {
        const selected = button.dataset.adminTab;
        document.querySelectorAll('[data-admin-tab]').forEach((tab) => {
            tab.classList.toggle('active', tab === button);
        });
        document.getElementById('adminCustomersPanel').hidden = selected !== 'customers';
        document.getElementById('adminPrizesPanel').hidden = selected !== 'prizes';
    });
});

document.getElementById('adminCustomerSearch').addEventListener('input', renderCustomers);

document.getElementById('adminPrizesForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const prizes = [...prizeList.querySelectorAll('.admin-prize-row')].map((row) => ({
        id: Number(row.dataset.prizeId),
        name: row.querySelector('[name="name"]').value,
        discountPercent: Number(row.querySelector('[name="discountPercent"]').value),
        tomoeLevel: Number(row.querySelector('[name="tomoeLevel"]').value),
        probabilityWeight: Number(row.querySelector('[name="probabilityWeight"]').value),
        active: row.querySelector('[name="active"]').checked
    }));
    try {
        const result = await adminRequest('/api/admin/prizes', {
            method: 'PUT',
            body: JSON.stringify({ prizes })
        });
        showAdminMessage(result.message);
        window.dispatchEvent(new CustomEvent('prizes-updated'));
    } catch (error) {
        showAdminMessage(error.message, true);
    }
});

window.addEventListener('hashchange', () => {
    if (window.location.hash === '#administracao') adminSection.hidden = false;
});
