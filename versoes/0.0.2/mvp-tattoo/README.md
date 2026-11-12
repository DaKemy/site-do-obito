# Backend — Site do Obito 0.0.2

Este diretório contém a aplicação Flask e os arquivos do painel MVP da versão
principal 0.0.2. O servidor entrega o site, o painel e as APIs no mesmo
endereço. O código desta pasta não importa nem serve arquivos da versão 0.0.11.

Consulte [../README.md](../README.md) para configurar o ambiente, iniciar o
servidor e entender as variáveis exigidas.

## Componentes

- `app.py`: rotas Flask, autenticação, regras de fidelidade e conexão PostgreSQL.
- `public/`: interface HTML/CSS/JavaScript do painel em `/mvp`.
- `requirements.txt`: dependências Python.
- `server.js`: iniciador opcional do backend Python usando Node.js.
- `test_auth.py`: testes do fluxo de contas e giros.

As rotas incluem autenticação, confirmação e recuperação de e-mail, clientes,
giros, cupons, pedidos de tatuagem, fidelidade e administração.
