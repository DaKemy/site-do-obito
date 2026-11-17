const spinButton = document.getElementById('spinButton');
const wheel = document.querySelector('.wheel');

if (spinButton && wheel) {
  spinButton.addEventListener('click', () => {
    const spinAmounts = [0, 45, 90, 135, 180, 225, 270, 315];
    const randomIndex = Math.floor(Math.random() * spinAmounts.length);
    const finalRotation = 720 + spinAmounts[randomIndex];

    wheel.style.transform = `rotate(${finalRotation}deg)`;
  });
}
