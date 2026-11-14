// Iniciador opcional: usa Node.js para executar o backend Flask em Python.
const { spawn } = require('node:child_process');

const isWindows = process.platform === 'win32';
const python = process.env.PYTHON || (isWindows ? 'py' : 'python3');
const args = isWindows ? ['-3', 'app.py'] : ['app.py'];

// Repassa ambiente/terminal ao filho para configurações e logs continuarem visíveis.
const backend = spawn(python, args, {
  cwd: __dirname,
  env: { ...process.env, PORT: process.env.PORT || '5000' },
  stdio: 'inherit'
});

// Propaga falha de inicialização e o código de saída do processo Python.
backend.on('error', (error) => {
  console.error(`Não foi possível iniciar o backend Python (${python}): ${error.message}`);
  process.exitCode = 1;
});

backend.on('exit', (code, signal) => {
  process.exitCode = code || (signal ? 1 : 0);
});

// Fecha o processo Python quando o serviço Node receber pedido de encerramento.
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => backend.kill(signal));
}
