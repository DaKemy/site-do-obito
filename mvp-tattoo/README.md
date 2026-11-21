# Backend — Site do Obito 0.0.2

Este diretório contém a aplicação Flask e as APIs da versão principal 0.0.2.
O servidor entrega o site e as APIs no mesmo endereço. A interface HTML antiga
do painel foi removida; `/mvp` redireciona para a página principal.

Consulte [../README.md](../README.md) para configurar o ambiente, iniciar o
servidor e entender as variáveis exigidas.

## Componentes

- `app.py`: configuração e conexão PostgreSQL, validações, envio de e-mail,
  rotas Flask e regras de contas, roleta, fidelidade e administração. Os
  cabeçalhos `# ── ... ──` separam os grupos de rotas; docstrings explicam os
  helpers e operações que não são óbvios.
- `manage_admin.py`: ferramenta de terminal para criar ou redefinir uma conta
  de desenvolvedor; lê a senha sem exibi-la e grava somente o hash.
- As rotas administrativas protegidas permitem gerenciar contas, redefinir
  senhas e atualizar as configurações dos prêmios da roleta.
- `public/`: recursos estáticos remanescentes do painel antigo; não há mais uma
  página HTML do painel.
- `requirements.txt`: dependências Python.
- `server.js`: iniciador opcional do backend Python usando Node.js.
- `test_registration.py`, `test_manage_admin.py`, `test_auth.py` e
  `test_email.py`: testes do cadastro, ferramenta administrativa, contas/giros
  e envio por API HTTPS do Gmail.

## Mapa das APIs

| Grupo de rotas | Finalidade | Acesso |
| --- | --- | --- |
| `/api/health`, `/api/prizes` | Verificar disponibilidade e listar prêmios ativos. | Público |
| `/api/auth/...` | Cadastro, confirmação, login/logout, sessão e recuperação de senha. | Público ou sessão de cliente, conforme a ação |
| `/api/customers/...`, `/api/spins/roll` | Consultar perfil/fidelidade e consumir um giro disponível. | Cliente autenticado; dados limitados à própria conta |
| `/api/admin/login`, `/api/admin/me`, `/api/admin/logout` | Iniciar, consultar e encerrar a sessão de desenvolvedor. | Credenciais administrativas |
| `/api/admin/customers/...`, `/api/admin/prizes` | Consultar/alterar clientes, redefinir senhas e configurar prêmios. | Desenvolvedor autenticado |
| `/api/tattoos/request`, `/api/tattoos/approve` | Receber uma ideia de tatuagem e registrar uma sessão aprovada. | Cliente para pedido; desenvolvedor para aprovação |

As respostas de erro da API incluem um código HTTP e uma mensagem. O JavaScript
mostra essa mensagem para a pessoa; ao depurar, confira a rota e o código HTTP
antes de alterar banco ou regras.

Por padrão, o cadastro ativa a conta e concede o giro inicial sem enviar e-mail.
Defina `REQUIRE_EMAIL_VERIFICATION=1` somente depois de configurar o serviço de
e-mail para voltar ao fluxo de confirmação.

Para criar uma conta administrativa, execute `py manage_admin.py` sem
argumentos. O programa pede usuário e senha, oculta a senha digitada e pede
confirmação antes de alterar o banco definido por `DATABASE_URL`. Confira se
esse banco é o ambiente que deseja configurar. Para redefinir uma conta
existente, use `py manage_admin.py reset-password USUARIO`.

## Formato das explicações

Em Python, procure comentários que começam com `#` e docstrings entre aspas
triplas. O código do navegador usa `//` para explicar funções e eventos. CSS
usa `/* ... */`. Os comentários descrevem a responsabilidade de cada parte;
as regras executáveis continuam sendo as próprias instruções do programa.

As rotas incluem autenticação, confirmação opcional e recuperação de e-mail, clientes,
giros, cupons, pedidos de tatuagem, fidelidade e administração.

## Executar os testes

`test_registration.py`, `test_manage_admin.py` e `test_email.py` usam serviços
simulados e não precisam de banco nem de credenciais de e-mail. `test_auth.py`
usa `DATABASE_URL` para criar e remover um schema temporário, então rode-o
somente contra um banco de testes isolado:

```powershell
py -m unittest test_registration test_manage_admin test_email -v
py -m unittest test_auth -v
```
