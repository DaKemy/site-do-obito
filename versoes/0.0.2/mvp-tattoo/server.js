const { spawn } = require('node:child_process');

const isWindows = process.platform === 'win32';
const python = process.env.PYTHON || (isWindows ? 'py' : 'python3');
const args = isWindows ? ['-3', 'app.py'] : ['app.py'];

const backend = spawn(python, args, {
  cwd: __dirname,
  env: { ...process.env, PORT: process.env.PORT || '5000' },
  stdio: 'inherit'
});

backend.on('error', (error) => {
  console.error(`Não foi possível iniciar o backend Python (${python}): ${error.message}`);
  process.exitCode = 1;
});

backend.on('exit', (code, signal) => {
  process.exitCode = code || (signal ? 1 : 0);
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => backend.kill(signal));
}
