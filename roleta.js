const rouletteStatus = document.getElementById('rouletteStatus');
const spinCount = document.getElementById('spinCount');

window.addEventListener('wheel-prizes-loaded', () => {
    rouletteStatus.textContent = 'Roleta pronta.';
    spinCount.textContent = 'Giros ilimitados de demonstração.';
});

window.addEventListener('wheel-prizes-error', (event) => {
    rouletteStatus.textContent = event.detail || 'Não foi possível carregar os prêmios.';
    spinCount.textContent = '';
});
