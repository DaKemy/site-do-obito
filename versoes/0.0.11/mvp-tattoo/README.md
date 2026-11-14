# Roleta da Fidelidade — versão 0.0.11

O Flask serve o site principal, o painel MVP e as APIs no mesmo endereço.
GitHub Pages não executa Flask: hospede este backend em um serviço Python.
O app usa PostgreSQL (Neon) por meio da variável `DATABASE_URL`.

## Configuração

Configure as variáveis no ambiente do serviço de hospedagem; não as coloque no
código nem no Git. Para desenvolvimento local, o `python-dotenv` carrega o
arquivo `.env` na raiz da versão, que permanece ignorado pelo Git:

- `FLASK_SECRET_KEY`: segredo longo e aleatório para assinar sessões.
- `CPF_HASH_SECRET`: segredo aleatório, estável e exclusivo para gerar hashes
  dos CPFs. Não o troque sem um plano de migração, pois os hashes existentes
  deixarão de corresponder.
- `ADMIN_USERNAME` e `ADMIN_PASSWORD`: credenciais administrativas fortes.
- `PUBLIC_BASE_URL`: URL pública HTTPS do site, sem barra final.
- `SESSION_COOKIE_SECURE=1`: exige HTTPS para o cookie de sessão.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`: servidor e remetente de e-mail.
- `SMTP_USERNAME` e `SMTP_PASSWORD`: credenciais SMTP, quando exigidas.
- `SMTP_USE_TLS=1` (padrão) ou `SMTP_USE_SSL=1`: proteção da conexão SMTP.
- `PORT`: porta fornecida pela hospedagem (padrão local: `5000`).

Defina `DATABASE_URL` no `.env` local ou como variável de ambiente secreta do
serviço de hospedagem. O app usa o endpoint pooled para as conexões normais.

Instale `requirements.txt` e dê duplo clique em `app.py` para iniciar o site e
abri-lo no navegador em `http://127.0.0.1:5000`. A janela do terminal mantém o
servidor ativo; feche-a para encerrar. A inicialização cria as tabelas e os
prêmios padrão no Neon. Para hospedagem, inicie com `python app.py` e defina
`HOST=0.0.0.0` no serviço.

## Cadastro e dados pessoais

O cadastro verifica os dígitos do CPF, impede CPF/e-mail/telefone duplicados e
exige confirmação do e-mail. A validação matemática não confirma que o CPF foi
emitido nem que pertence à pessoa. O CPF não é armazenado em texto puro: o
banco guarda apenas um HMAC com `CPF_HASH_SECRET`. Senhas usam hash apropriado;
links de confirmação e redefinição expiram e seus tokens não são armazenados em
texto puro.

Sem SMTP configurado, o cadastro não afirma que enviou a confirmação. Os
arquivos enviados permanecem no disco local. Em produção, use armazenamento
persistente para uploads ou um serviço de objetos, e mantenha backup do banco.

## Rotas

- `/`: site principal.
- `/mvp`: painel de fidelidade.
- `/api/health`: verificação simples do backend.
