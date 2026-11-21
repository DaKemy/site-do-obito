const rouletteStatus = document.getElementById('rouletteStatus');

window.addEventListener('wheel-prizes-loaded', () => {
    rouletteStatus.textContent = 'Roleta pronta.';
});

window.addEventListener('wheel-prizes-error', (event) => {
    rouletteStatus.textContent = event.detail || 'Não foi possível carregar os prêmios.';
});
