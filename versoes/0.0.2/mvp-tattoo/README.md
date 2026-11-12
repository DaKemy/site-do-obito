# Backend — Site do Obito 0.0.2

Este diretório contém a aplicação Flask e as APIs da versão principal 0.0.2.
O servidor entrega o site e as APIs no mesmo endereço. A interface HTML antiga
do painel foi removida; `/mvp` redireciona para a página principal. O código
desta pasta não importa nem serve arquivos da versão 0.0.11.

Consulte [../README.md](../README.md) para configurar o ambiente, iniciar o
servidor e entender as variáveis exigidas.

## Componentes

- `app.py`: rotas Flask, autenticação, regras de fidelidade e conexão PostgreSQL.
- `manage_admin.py`: criação e redefinição segura de contas administrativas.
- As rotas administrativas protegidas permitem gerenciar contas, redefinir
  senhas e atualizar as configurações dos prêmios da roleta.
- `public/`: recursos estáticos remanescentes do painel antigo; não há mais uma
  página HTML do painel.
- `requirements.txt`: dependências Python.
- `server.js`: iniciador opcional do backend Python usando Node.js.
- `test_auth.py` e `test_email.py`: testes do fluxo de contas, giros e envio por
  API HTTPS do Gmail.

As rotas incluem autenticação, confirmação e recuperação de e-mail, clientes,
giros, cupons, pedidos de tatuagem, fidelidade e administração.
