# Site do Obito — versão 0.0.2

Esta pasta contém uma cópia executável e independente do site, além do guia de
arquivos em `guia.html`. O HTML, o CSS, o JavaScript, o backend Flask e os
arquivos do painel MVP estão dentro desta própria pasta. A aplicação não lê
arquivos da pasta `0.0.11`.

**A 0.0.2 é a versão principal do projeto. A 0.0.11 está arquivada como
histórico**, assim como as versões 0.0.0 e 0.0.1.

## Preparar o ambiente

1. Instale Python 3.10 ou superior e PostgreSQL, ou configure um banco
   PostgreSQL hospedado.
2. A configuração `.env` local foi migrada da 0.0.11 para preservar a conexão
   Neon e o segredo de hash de CPF usados pelos dados existentes. Em uma
   instalação nova, copie `.env.example` para `.env` e preencha as variáveis.
   Não sobrescreva o `.env` local migrado.
3. Configure `DATABASE_URL`, `FLASK_SECRET_KEY`, `CPF_HASH_SECRET`, as
   credenciais administrativas e, quando for enviar e-mails, as variáveis SMTP.
   Mantenha os segredos fora do Git.
4. Abra um terminal na pasta `versoes/0.0.2/mvp-tattoo` e instale as
   dependências:

   ```powershell
   py -m pip install -r requirements.txt
   ```

5. Inicie o site:

   ```powershell
   py app.py
   ```

O Flask cria as tabelas e os prêmios padrão no banco configurado, depois abre o
site em `http://127.0.0.1:5000`. O guia está disponível em
`http://127.0.0.1:5000/guia.html`. Para encerrar, feche o terminal do servidor.

## Arquivos principais

- `index.html`, `styles.css`, `login.js`, `script.js` e `admin.js`: página
  principal, conta do cliente, roleta e painel administrativo.
- `esqueci-senha.html`: solicitação de recuperação e definição de nova senha.
- `mvp-tattoo/app.py`: API Flask, autenticação, regras de negócio e acesso ao
  PostgreSQL.
- `mvp-tattoo/manage_admin.py`: utilitário para criar ou redefinir contas do
  painel do desenvolvedor; solicita as senhas sem exibi-las e grava somente o
  hash no banco.
- `mvp-tattoo/public/`: recursos estáticos remanescentes do painel antigo. A
  interface antiga foi removida; `/mvp` agora redireciona para a página
  principal da versão 0.0.2.
- `mvp-tattoo/requirements.txt`: dependências Python.
- `mvp-tattoo/test_auth.py`: testes do fluxo de autenticação e giro.
- `guia.html`: mapa interativo do projeto e explicações dos fluxos.

## Notas de operação

- GitHub Pages não executa Flask. Para disponibilizar login e banco na internet,
  hospede o backend em um serviço compatível com Python e configure as variáveis
  de ambiente como segredos do serviço.
- Para confirmação e recuperação de senha no Render, configure
  `EMAIL_PROVIDER=gmail_api` e as credenciais OAuth do Gmail como segredos.
  Esse modo envia pela API HTTPS do Gmail e evita depender de SMTP de saída.
  Ative a Gmail API no Google Cloud e configure `GMAIL_CLIENT_ID`,
  `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` e `GMAIL_FROM` no Render; não
  compartilhe esses valores no chat. SMTP continua disponível em ambientes que
  permitem conexões SMTP.
- O acesso do cliente continua no formulário normal de cadastro/login. O ícone
  de catraca no canto superior direito abre um painel separado, exclusivo para
  contas de desenvolvedor. As senhas administrativas ficam armazenadas como
  hash no banco; para criar ou redefinir uma conta localmente, use
  `py manage_admin.py create usuario` ou `py manage_admin.py reset-password usuario`
  a partir de `mvp-tattoo`.
- Na primeira inicialização após a atualização, a conta administrativa já
  configurada em `ADMIN_USERNAME` e `ADMIN_PASSWORD` é migrada para a tabela
  protegida por hash. Depois de confirmar o primeiro acesso no painel, remova
  essas duas variáveis do Render; contas adicionais e redefinições são feitas
  pelo utilitário Python.
- O painel em **Administração** permite buscar, editar e excluir usuários,
  redefinir senhas e configurar os prêmios e probabilidades da roleta. A
  exclusão também remove os dados associados e as imagens anexadas às
  solicitações de tatuagem. Senhas existentes e segredos de ambiente nunca são
  exibidos no painel.
- O arquivo `.env` e os dados de banco não devem ser enviados ao Git.
- Esta cópia usa o banco indicado por seu próprio `DATABASE_URL`; não copia os
  dados da aplicação SQLite antiga.
