// Controla os prêmios mostrados e a animação visual da roleta principal.
const spinButton = document.getElementById('spinButton');
const wheel = document.querySelector('.wheel');
const spinMessage = document.getElementById('spinMessage');
let currentRotation = 0;
let activePrizeCount = document.querySelectorAll('.wheel .segment').length;
const wheelColors = ['#b65200', '#990000', '#e74d06', '#000000', '#ff4901', '#7e0a0a'];

async function refreshWheelPrizes() {
    // Busca a lista oficial de prêmios; os dados exibidos vêm do servidor.
    const response = await fetch('/api/prizes');
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Não foi possível carregar os prêmios.');
    const prizes = result.prizes;
    if (!prizes.length) throw new Error('A roleta não tem prêmios ativos.');
    activePrizeCount = prizes.length;

    const wheelSegments = [...document.querySelectorAll('.wheel .segment')];
    while (wheelSegments.length < prizes.length) {
        const segment = document.createElement('span');
        segment.className = 'segment';
        wheel.append(segment);
        wheelSegments.push(segment);
    }
    wheelSegments.forEach((segment, index) => {
        segment.hidden = index >= prizes.length;
    });
    wheelSegments.slice(0, prizes.length).forEach((segment, index) => {
        segment.className = `segment s${index + 1}`;
        const centerAngle = ((index + 0.5) * 360) / prizes.length;
        segment.textContent = `${prizes[index].discount_percent}%`;
        segment.style.transform = `rotate(${centerAngle}deg) translateY(calc(-1 * var(--wheel-label-radius)))`;
    });
    const gradient = prizes.map((_, index) => {
        const start = (index * 360) / prizes.length;
        const end = ((index + 1) * 360) / prizes.length;
        return `${wheelColors[index % wheelColors.length]} ${start}deg ${end}deg`;
    });
    wheel.style.background = `conic-gradient(${gradient.join(', ')})`;
}

if (wheel) {
    // Inicializa a roleta e a atualiza quando o painel salva novas configurações.
    refreshWheelPrizes().catch((error) => {
        spinMessage.textContent = error.message;
        spinMessage.classList.add('error');
    });
    window.addEventListener('prizes-updated', () => {
        refreshWheelPrizes().catch((error) => {
            spinMessage.textContent = error.message;
            spinMessage.classList.add('error');
        });
    });
}

async function requestSpin() {
    // Solicita ao backend o resultado oficial (o navegador não sorteia o prêmio).
    const response = await fetch('/api/spins/roll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Não foi possível girar a roleta.');
    return result;
}

if (spinButton && wheel) {
    // Anima a roleta até o segmento correspondente ao resultado da API.
    spinButton.addEventListener('click', async () => {
        spinButton.disabled = true;
        spinMessage.textContent = '';
        spinMessage.classList.remove('error');
        try {
            const response = await requestSpin();
            const targetAngle = 360 - ((response.result.segmentIndex + 0.5) * 360 / activePrizeCount);
            const currentAngle = ((currentRotation % 360) + 360) % 360;
            const rotationDelta = 360 * 6 + ((targetAngle - currentAngle + 360) % 360);
            currentRotation += rotationDelta;
            wheel.style.transform = `rotate(${currentRotation}deg)`;
            spinMessage.textContent = `${response.result.prizeName}: ${response.result.discountPercent}% de desconto.`;
        } catch (error) {
            spinMessage.textContent = error.message;
            spinMessage.classList.add('error');
        } finally {
            spinButton.disabled = false;
        }
    });
}
