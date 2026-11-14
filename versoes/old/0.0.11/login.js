const accountMessage = document.getElementById('accountMessage');
const registrationForm = document.getElementById('CadastroSite');
const loginForm = document.getElementById('EntrarPainel');
const resendButton = document.getElementById('resendVerification');

function showAccountMessage(message, isError = false) {
    if (!accountMessage) return;
    accountMessage.textContent = message;
    accountMessage.classList.toggle('error', isError);
}

function setFormMode(mode) {
    const entering = mode === 'login';
    loginForm.style.display = entering ? 'grid' : 'none';
    registrationForm.style.display = entering ? 'none' : 'grid';
    document.getElementById('Indicador').style.transform = entering ? 'translateX(0)' : 'translateX(100%)';
    resendButton.hidden = true;
    showAccountMessage('');
}

window.mostrarEntrar = () => setFormMode('login');
window.mostrarCadastro = () => setFormMode('register');

document.getElementById('tabEntrar')?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') setFormMode('login');
});
document.getElementById('tabCadastro')?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') setFormMode('register');
});

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Não foi possível concluir a solicitação.');
    return result;
}

registrationForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const fields = new FormData(registrationForm);
    const payload = Object.fromEntries(fields.entries());
    try {
        const result = await postJson('/api/auth/register', payload);
        showAccountMessage(result.message);
        registrationForm.reset();
    } catch (error) {
        showAccountMessage(error.message, true);
    }
});

loginForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const fields = new FormData(loginForm);
    try {
        const result = await postJson('/api/auth/login', Object.fromEntries(fields.entries()));
        showAccountMessage('Acesso confirmado. Seu giro já pode ser usado.');
        resendButton.hidden = true;
        window.dispatchEvent(new CustomEvent('customer-authenticated', { detail: result }));
    } catch (error) {
        showAccountMessage(error.message, true);
        resendButton.hidden = !error.message.includes('Confirme seu e-mail');
    }
});

resendButton?.addEventListener('click', async () => {
    const identifier = loginForm.elements.identifier.value.trim();
    const password = loginForm.elements.password.value;
    try {
        const result = await postJson('/api/auth/resend-verification', { identifier, password });
        showAccountMessage(result.message);
        resendButton.hidden = true;
    } catch (error) {
        showAccountMessage(error.message, true);
    }
});

const verificationToken = new URLSearchParams(window.location.search).get('verificar');
if (verificationToken) {
    postJson('/api/auth/verify-email', { token: verificationToken })
        .then((result) => {
            window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
            showAccountMessage(result.message);
            window.dispatchEvent(new CustomEvent('customer-authenticated'));
        })
        .catch((error) => showAccountMessage(error.message, true));
}

if (registrationForm) {
    document.getElementById('telefone')?.addEventListener('input', (event) => {
        const digits = event.target.value.replace(/\D/g, '').slice(0, 11);
        const area = digits.slice(0, 2);
        const subscriber = digits.slice(2);
        event.target.value = digits.length > 2
            ? `(${area}) ${subscriber.slice(0, 5)}${subscriber.length > 5 ? `-${subscriber.slice(5)}` : ''}`
            : digits;
    });
}

if (registrationForm && loginForm) setFormMode('login');

fetch('/api/auth/me')
    .then((response) => response.ok ? response.json() : null)
    .then((result) => {
        if (result?.customer) {
            showAccountMessage(`Bem-vindo(a), ${result.customer.name}.`);
            window.dispatchEvent(new CustomEvent('customer-authenticated', {
                detail: { customerId: result.customer.id }
            }));
        }
    })
    .catch(() => showAccountMessage('Não foi possível verificar sua sessão. Atualize a página.', true));

const recoveryForm = document.getElementById('RecuperarSenha');
const resetForm = document.getElementById('ResetarSenha');
const resetToken = new URLSearchParams(window.location.search).get('token');

if (recoveryForm) {
    if (resetToken) {
        recoveryForm.hidden = true;
        resetForm.hidden = false;
    }

    recoveryForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const email = new FormData(recoveryForm).get('email');
        try {
            const result = await postJson('/api/auth/password-reset', { email });
            showAccountMessage(result.message);
        } catch (error) {
            showAccountMessage(error.message, true);
        }
    });
}

if (resetForm) {
    resetForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const password = new FormData(resetForm).get('password');
        try {
            const result = await postJson('/api/auth/reset-password', { token: resetToken, password });
            showAccountMessage(result.message);
            resetForm.reset();
        } catch (error) {
            showAccountMessage(error.message, true);
        }
    });
}
