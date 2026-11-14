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

## Como entender e alterar o código

Comece por `guia.html`: o índice pesquisável explica para que serve cada
arquivo e mostra como cadastro, login, roleta e administração passam pelas
camadas. Os comentários no código usam a sintaxe própria de cada linguagem:
`<!-- ... -->` no HTML, `//` no JavaScript, `#` no Python e `/* ... */` no CSS.
Esses comentários explicam o papel de uma seção ou função sem alterar o que o
site executa.

Uma mudança na interface normalmente percorre este caminho:

1. `index.html` define a seção, os campos e os identificadores dos controles.
2. `styles.css` define cores, tamanhos, disposição e adaptação para telas menores.
3. `login.js`, `script.js` ou `admin.js` reage aos cliques e envia pedidos HTTP.
4. `mvp-tattoo/app.py` valida os dados e aplica as regras antes de responder.
5. O PostgreSQL persiste contas, progresso, giros e configurações.

Use `name` dos campos HTML como contrato dos dados enviados à API e confira
sempre as duas pontas antes de renomeá-lo. Arquivos em `versoes/old/` são
referências históricas: uma alteração do site ativo deve começar em
`versoes/0.0.2/`, não numa cópia antiga.

## Preparar o VS Code e colaborar

O repositório fornece recomendações de extensões Python/Pylance e integração
GitHub em `.vscode/extensions.json`, além de tarefas para iniciar o Flask e
rodar os testes simulados de e-mail em `.vscode/tasks.json`. Ao abrir esta pasta
como workspace no VS Code, aceite instalar as extensões recomendadas se desejar.

Para configurar uma cópia local no Windows, use o script
[`scripts/preparar-colaboradora.ps1`](../../scripts/preparar-colaboradora.ps1)
na raiz do clone. Ele pode pedir autorização para instalar Git via `winget`,
clona/atualiza o repositório sem sobrescrever arquivos locais e abre esta
pasta no VS Code. Execute-o em um PowerShell **local**; o terminal de uma sessão
Live Share remota não instala ferramentas no computador da convidada.

Cada pessoa deve usar sua própria branch, publicar commits e abrir Pull Request
para `main`. Isso mantém o histórico e permite revisar mudanças antes de
integrá-las. Para atualizar a branch principal local sem conflitos:

```powershell
git pull --ff-only origin main
```

O GitHub não baixa automaticamente as mudanças de outra pessoa e o Live Share
não substitui esse fluxo. O VS Code também oferece a tarefa **Site do Obito:
iniciar Flask** em `Terminal > Run Task`; ela requer dependências Python e um
`.env` privado configurado. Live Server pode mostrar páginas estáticas, mas não
atende as APIs do backend.

### Mapa das páginas e responsabilidades

| Arquivo | O que sua colega encontra nele |
| --- | --- |
| `index.html` | Cabeçalho e navegação, apresentação/roleta, etapas, benefícios, cadastro/login do cliente e painel do desenvolvedor. |
| `esqueci-senha.html` | Formulário para pedir o link de recuperação e, com token, escolher uma senha nova. |
| `guia.html` | Índice pesquisável dos arquivos, explicação das camadas e tutoriais dos principais fluxos. |
| `styles.css` | Paleta, tipografia, tamanhos, disposição dos componentes, painel e regras para telas menores. |
| `login.js` | Abas de cadastro/login, comunicação de conta, confirmação de e-mail e recuperação de senha. |
| `script.js` | Busca dos prêmios, pedido de giro ao servidor e animação visual do resultado. |
| `admin.js` | Sessão do desenvolvedor, busca/edição/exclusão de clientes e configuração da roleta. |
| `mvp-tattoo/app.py` | API Flask, validações, sessões, banco, mensagens de e-mail e regras de negócio. |
| `mvp-tattoo/manage_admin.py` | Comandos protegidos para criar uma conta de desenvolvedor ou redefinir sua senha. |
| `mvp-tattoo/test_auth.py` | Testes de cadastro, privacidade, permissões, roleta, recuperação e fidelidade. |
| `mvp-tattoo/test_email.py` | Testes simulados da integração Gmail API; não envia mensagens reais. |
| `mvp-tattoo/server.js` | Iniciador opcional que executa o processo Python usando Node.js. |
| `mvp-tattoo/public/` | Arquivos que restaram da interface antiga do MVP; não são a interface principal atual. |

### Caminho das ações mais comuns

- **Cadastro/login:** `index.html` → `login.js` → `/api/auth/...` em `app.py` →
  PostgreSQL. O cadastro exige confirmação de e-mail antes de liberar o giro.
- **Recuperar senha:** `esqueci-senha.html` → `login.js` →
  `/api/auth/password-reset` para pedir o link e `/api/auth/reset-password`
  para salvar a senha nova.
- **Girar:** `script.js` pede `/api/spins/roll`; o servidor valida a sessão,
  sorteia e grava o resultado. O navegador só anima o segmento retornado.
- **Administrar:** a catraca abre o painel em `index.html`; `admin.js` chama
  rotas `/api/admin/...`, que exigem uma sessão de desenvolvedor válida.
- **Fidelidade:** o desenvolvedor aprova sessões de tatuagem; `app.py` soma o
  progresso e cria um giro adicional a cada três conclusões.

### Termos usados nos comentários

- **Rota/API:** endereço HTTP atendido pelo backend, por exemplo
  `/api/auth/login`.
- **Sessão:** cookie protegido que permite ao servidor reconhecer a pessoa
  autenticada sem reenviar a senha a cada ação.
- **Hash de senha:** representação não reversível usada para conferir uma
  senha sem guardar o texto digitado.
- **HMAC do CPF:** resumo protegido por uma chave secreta, usado para localizar
  uma conta sem armazenar o CPF em texto puro.
- **Peso do prêmio:** valor relativo usado no sorteio; aumentar o peso aumenta
  a chance relativa, não garante que o prêmio será escolhido.

### Testes

Os testes de e-mail usam respostas simuladas e podem ser executados sem enviar
mensagem:

```powershell
cd versoes/0.0.2/mvp-tattoo
py -m unittest test_email -v
```

`test_auth.py` cobre fluxos de ponta a ponta e precisa de PostgreSQL acessível
em `DATABASE_URL`. Ele cria e remove um schema temporário; execute-o somente
com uma base de testes dedicada, nunca apontando para o banco de produção:

```powershell
py -m unittest test_auth -v
```

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
