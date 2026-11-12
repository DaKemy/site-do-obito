# Roleta da Fidelidade — versão 0.0.11

O Flask serve o site principal, o painel MVP e as APIs no mesmo endereço. O
GitHub Pages não executa Flask: publique o código no GitHub e hospede este
backend separadamente em um serviço que execute Python.

## Configuração

Configure as variáveis no ambiente do serviço de hospedagem; não as coloque no
código nem no Git:

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

Instale `requirements.txt` e inicie com `python app.py` ou `npm start` nesta
pasta. Em desenvolvimento local por HTTP, defina `SESSION_COOKIE_SECURE=0`.
Não execute `FLASK_DEBUG=1` em produção.

## Cadastro e dados pessoais

O cadastro verifica os dígitos do CPF, impede CPF/e-mail/telefone duplicados e
exige confirmação do e-mail. A validação matemática não confirma que o CPF foi
emitido nem que pertence à pessoa. O CPF não é armazenado em texto puro: o
banco guarda apenas um HMAC com `CPF_HASH_SECRET`. Senhas usam hash apropriado;
links de confirmação e redefinição expiram e seus tokens não são armazenados em
texto puro.

Sem SMTP configurado, o cadastro não afirma que enviou a confirmação. O banco
SQLite e os arquivos enviados são locais e não devem ser publicados; mantenha
backup e armazenamento persistente no serviço de hospedagem.

## Rotas

- `/`: site principal.
- `/mvp`: painel de fidelidade.
- `/api/health`: verificação simples do backend.
