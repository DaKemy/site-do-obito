# Site do Obito

Site de fidelidade para clientes de tatuagem. A pessoa cria uma conta, recebe
um giro na roleta e pode receber novos giros conforme progride no programa de
fidelidade. O projeto também tem um painel separado para a equipe de
desenvolvimento administrar contas e prêmios.

## Qual pasta é a versão atual?

**A versão principal está na raiz do repositório.** Comece por `index.html`,
`roleta.html` e `mvp-tattoo/app.py`. As cópias históricas foram removidas para
evitar confusão; novas alterações devem ficar na raiz ou em `mvp-tattoo/`.

## Colaboração no VS Code

Se você usa o clone do GitHub Desktop em
`D:\AsVeizDesenvolve\site-do-obito`, abra essa pasta no VS Code e siga
[`INSTRUCOES-MUICHI1.md`](./INSTRUCOES-MUICHI1.md). O Copilot Chat encontra
orientações do projeto em `.github/copilot-instructions.md`; o prompt
**Preparar Site do Obito (Muichi1)** está em `.github/prompts/`.

## O que cada parte faz?

| Parte | Responsabilidade |
| --- | --- |
| `index.html` | Página inicial, cadastro/login e acesso ao painel do desenvolvedor. |
| `admin.html` | Login e painel administrativo em uma página separada. |
| `roleta.html` | Roleta pública em modo de demonstração temporário. |
| `esqueci-senha.html` | Telas para pedir a recuperação e salvar uma senha nova. |
| `styles.css` | Cores, tipografia, layout e adaptação para celular. |
| `login.js` | Cadastro, login do cliente, confirmação opcional e recuperação de conta. |
| `script.js` | Atualização visual e animação de um resultado demonstrativo escolhido pelo servidor. |
| `roleta.js` | Mensagens de carregamento e estado da roleta demonstrativa. |
| `admin.js` | Interface do painel exclusivo de desenvolvedor. |
| `mvp-tattoo/app.py` | Backend Flask: API, validações, sessões, regras de fidelidade e banco PostgreSQL. |
| `mvp-tattoo/manage_admin.py` | Criação de conta administrativa ou redefinição de senha pelo terminal. |
| `mvp-tattoo/test_*.py` | Testes de cadastro, autenticação e envio simulado de e-mail. |

O caminho típico de uma ação é:

```text
HTML (tela) → JavaScript (pedido HTTP) → Flask (validação e regras) → PostgreSQL
```

## Perfis de acesso

- **Cliente:** pode se cadastrar sem confirmação por e-mail enquanto
  `REQUIRE_EMAIL_VERIFICATION=0` e consultar sua conta, giros e progresso.
  Depois de configurar o serviço de e-mail, a confirmação pode ser reativada
  definindo essa variável como `1`.
- **Roleta:** temporariamente, qualquer visitante pode girar à vontade em modo
  de demonstração. Esses giros não são gravados e não geram cupons nem descontos
  reais. O endpoint de giros reais continua exigindo autenticação e saldo.
- **Desenvolvedor:** entra pela catraca na página inicial. Pode administrar
  clientes, redefinir senhas e alterar os prêmios. Esse acesso é separado do
  login de cliente.

## Executar localmente

1. Instale Python 3.10+ e PostgreSQL, ou prepare um banco PostgreSQL de teste.
2. Na raiz do projeto, copie `.env.example` para `.env` e preencha as
   configurações necessárias. Não substitua uma configuração `.env` já
   existente sem entender seus dados.
3. No PowerShell, instale e inicie o backend:

   ```powershell
   cd "mvp-tattoo"
   py -m pip install -r requirements.txt
   py app.py
   ```

4. Abra `http://127.0.0.1:5000`. A roleta fica em
   `http://127.0.0.1:5000/roleta.html` e a administração em
   `http://127.0.0.1:5000/admin.html`.

Por padrão, o cadastro ativa a conta imediatamente e não envia e-mail. Para
exigir confirmação, configure o envio de e-mail e defina
`REQUIRE_EMAIL_VERIFICATION=1` no ambiente privado do servidor.

## Trabalhar em conjunto no GitHub

Cada pessoa trabalha em um clone local do mesmo repositório. Baixar a cópia
pública não exige autenticação; para enviar alterações, a pessoa precisa entrar
no VS Code com sua própria conta GitHub e ter permissão de escrita no
repositório.

1. Abra o **PowerShell local do Windows** (não o terminal remoto do Live Share)
   e baixe o script da raiz do repositório:

   ```powershell
   $script = Join-Path $HOME "Downloads\preparar-colaboradora.ps1"
   Invoke-WebRequest "https://raw.githubusercontent.com/DaKemy/site-do-obito/main/scripts/preparar-colaboradora.ps1" -OutFile $script
   powershell -ExecutionPolicy Bypass -File $script
   ```

   O script pede confirmação antes de instalar Git pelo `winget`, clona o
   repositório público em `source\site-do-obito` e abre a raiz do projeto no
   VS Code. Se Git já estiver instalado e o clone existir, só atualiza `main`
   quando não há alterações locais. Ele não apaga arquivos nem envia mudanças.
2. No VS Code, entre com sua conta GitHub para poder publicar contribuições.
   O download público não precisa de login; para enviar commits, a conta precisa
   ter acesso ao repositório.
3. Faça cada tarefa em uma branch própria, por exemplo
   `muichi1/ajuste-da-home` ou `tiekenshi/correcao-da-roleta`. Use o Source
   Control do VS Code para criar a branch, revisar os arquivos, fazer commit e
   publicar a branch.
4. Abra um Pull Request para `main`; depois que as mudanças forem integradas,
   a outra pessoa atualiza sua cópia com `git pull --ff-only origin main`
   enquanto estiver na branch `main`.

O Live Share é opcional para edição em tempo real, mas não sincroniza commits
nem substitui o GitHub. Live Server mostra arquivos estáticos e não executa o
backend Flask. Para testar o site completo, use a tarefa **Site do Obito:
iniciar Flask** em `Terminal > Run Task` e configure `.env` localmente. Não
compartilhe esse arquivo.

## Testes

Os testes de e-mail usam chamadas simuladas e não enviam mensagens reais:

```powershell
cd "mvp-tattoo"
py -m unittest test_email -v
```

`test_auth.py` precisa de `DATABASE_URL` e cria/remove um schema temporário.
Execute-o somente contra um banco de testes isolado, nunca contra produção:

```powershell
cd "mvp-tattoo"
py -m unittest test_auth -v
```

## Segurança e publicação

- Nunca publique `.env`, senhas, tokens OAuth, connection strings, banco de
  dados ou arquivos enviados por clientes. O `.env.example` é apenas um modelo.
- Configure segredos no ambiente privado do serviço de hospedagem, não no
  código nem neste README.
- GitHub Pages serve arquivos estáticos e não executa o backend Flask. Para
  login, banco e APIs, hospede o backend em um serviço compatível com Python.
- Antes de publicar mudanças, confira se está editando os arquivos da raiz e
  se nenhum arquivo privado foi incluído no envio.

## Convenção dos comentários

Os comentários usam o formato de cada arquivo: `<!-- ... -->` no HTML, `//`
no JavaScript, `#` no Python e `/* ... */` no CSS. Eles explicam o papel dos
blocos e a relação entre as camadas sem mudar o comportamento do site.
