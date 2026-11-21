const rouletteStatus = document.getElementById('rouletteStatus');
const spinCount = document.getElementById('spinCount');
const rouletteSpinButton = document.getElementById('spinButton');
const loginRequired = document.getElementById('loginRequired');

function showProfileError(error) {
    rouletteStatus.textContent = error instanceof Error
        ? error.message
        : 'Não foi possível carregar sua conta.';
    rouletteSpinButton.disabled = true;
}

async function refreshCustomerSpins() {
    rouletteSpinButton.disabled = true;
    const authResponse = await fetch('/api/auth/me');
    if (!authResponse.ok) {
        throw new Error('Não foi possível verificar sua sessão. Tente novamente.');
    }

    const auth = await authResponse.json();
    if (!auth.customer) {
        rouletteStatus.textContent = 'Entre na sua conta para acessar a roleta.';
        spinCount.textContent = '';
        loginRequired.hidden = false;
        return;
    }

    loginRequired.hidden = true;
    const customerResponse = await fetch(`/api/customers/${auth.customer.id}`);
    if (!customerResponse.ok) {
        throw new Error('Não foi possível carregar seus giros. Atualize a página.');
    }

    const profile = await customerResponse.json();
    const availableSpins = profile.spins.filter((spin) => spin.status === 'pending').length;
    rouletteStatus.textContent = `Olá, ${profile.customer.name}!`;
    spinCount.textContent = availableSpins === 1
        ? 'Você tem 1 giro disponível.'
        : `Você tem ${availableSpins} giros disponíveis.`;
    rouletteSpinButton.disabled = availableSpins === 0;
}

refreshCustomerSpins().catch(showProfileError);
window.addEventListener('spin-attempt-finished', () => {
    refreshCustomerSpins().catch(showProfileError);
});
