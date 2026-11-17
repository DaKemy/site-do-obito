const spinButton = document.getElementById('spinButton');
const wheel = document.querySelector('.wheel');
const spinMessage = document.getElementById('spinMessage');
let currentRotation = 0;

async function requestSpin() {
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
    spinButton.addEventListener('click', async () => {
        spinButton.disabled = true;
        spinMessage.textContent = '';
        spinMessage.classList.remove('error');
        try {
            const response = await requestSpin();
            const targetAngle = 330 - (response.result.segmentIndex * 60);
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
