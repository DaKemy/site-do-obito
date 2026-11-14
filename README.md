# Site do Obito

Site de fidelidade para clientes de tatuagem. A pessoa cria uma conta, confirma
o e-mail, recebe um giro na roleta e pode receber novos giros conforme progride
no programa de fidelidade. O projeto também tem um painel separado para a
equipe de desenvolvimento administrar contas e prêmios.

## Qual pasta é a versão atual?

**A versão principal é [`versoes/0.0.2`](./versoes/0.0.2/).** As pastas
`versoes/old/` e `versoes/0.0.11/` são cópias históricas, não o ponto de partida
para mudanças novas.

Para entender a estrutura e acompanhar os fluxos, abra o
[guia interativo](./versoes/0.0.2/guia.html). As instruções completas de
instalação, configuração, testes e operação estão no
[README da versão principal](./versoes/0.0.2/README.md).

## O que cada parte faz?

| Parte | Responsabilidade |
| --- | --- |
| `versoes/0.0.2/index.html` | Conteúdo da página inicial, roleta, cadastro/login e painel do desenvolvedor. |
| `versoes/0.0.2/esqueci-senha.html` | Telas para pedir a recuperação e salvar uma senha nova. |
| `versoes/0.0.2/styles.css` | Cores, tipografia, layout e adaptação para celular. |
| `versoes/0.0.2/login.js` | Cadastro, login do cliente, confirmação e recuperação de conta. |
| `versoes/0.0.2/script.js` | Atualização visual da roleta e animação de um resultado escolhido no servidor. |
| `versoes/0.0.2/admin.js` | Interface do painel exclusivo de desenvolvedor. |
| `versoes/0.0.2/mvp-tattoo/app.py` | Backend Flask: API, validações, sessões, regras de fidelidade e banco PostgreSQL. |
| `versoes/0.0.2/mvp-tattoo/manage_admin.py` | Criação de conta administrativa ou redefinição de senha pelo terminal. |
| `versoes/0.0.2/mvp-tattoo/test_*.py` | Testes de integração da autenticação e testes simulados de e-mail. |
| `versoes/0.0.2/guia.html` | Mapa pesquisável dos arquivos e tutoriais dos principais fluxos. |

O caminho típico de uma ação é:

```text
HTML (tela) → JavaScript (pedido HTTP) → Flask (validação e regras) → PostgreSQL
```

## Perfis de acesso

- **Cliente:** usa cadastro/login, precisa confirmar o e-mail e pode consultar
  sua conta, seus giros e seu progresso.
- **Desenvolvedor:** entra pela catraca na página inicial. Pode administrar
  clientes, redefinir senhas e alterar os prêmios. Esse acesso é separado do
  login de cliente.

## Executar localmente

1. Instale Python 3.10+ e PostgreSQL, ou prepare um banco PostgreSQL de teste.
2. Na pasta `versoes/0.0.2`, copie `.env.example` para `.env` e preencha as
   configurações necessárias. Não substitua uma configuração `.env` já
   existente sem entender seus dados.
3. No PowerShell, instale e inicie o backend:

   ```powershell
   cd "versoes\0.0.2\mvp-tattoo"
   py -m pip install -r requirements.txt
   py app.py
   ```

4. Abra `http://127.0.0.1:5000`. O guia fica em
   `http://127.0.0.1:5000/guia.html`.

Mais detalhes e configurações de e-mail estão no
[README da versão principal](./versoes/0.0.2/README.md).

## Trabalhar em conjunto no GitHub

Cada pessoa trabalha em um clone local do mesmo repositório. Baixar a cópia
pública não exige autenticação; para enviar alterações, a pessoa precisa entrar
no VS Code com sua própria conta GitHub e ter permissão de escrita no
repositório.

1. Instale Git for Windows. O script abaixo pode oferecer sua instalação pelo
   `winget`, pedindo confirmação antes.
2. Baixe o repositório e abra a versão correta no VS Code pelo PowerShell local:

   ```powershell
   git clone --branch main --single-branch https://github.com/DaKemy/site-do-obito.git "$HOME\source\site-do-obito"
   cd "$HOME\source\site-do-obito"
   powershell -ExecutionPolicy Bypass -File ".\scripts\preparar-colaboradora.ps1"
   ```

   O script também reconhece a pasta padrão se já existir, atualiza `main`
   somente quando a cópia está limpa e abre `versoes\0.0.2` no VS Code. Ele não
   apaga arquivos nem envia alterações automaticamente.
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
cd "versoes\0.0.2\mvp-tattoo"
py -m unittest test_email -v
```

`test_auth.py` precisa de `DATABASE_URL` e cria/remove um schema temporário.
Execute-o somente contra um banco de testes isolado, nunca contra produção:

```powershell
py -m unittest test_auth -v
```

## Segurança e publicação

- Nunca publique `.env`, senhas, tokens OAuth, connection strings, banco de
  dados ou arquivos enviados por clientes. O `.env.example` é apenas um modelo.
- Configure segredos no ambiente privado do serviço de hospedagem, não no
  código nem neste README.
- GitHub Pages serve arquivos estáticos e não executa o backend Flask. Para
  login, banco e APIs, hospede o backend em um serviço compatível com Python.
- Antes de publicar mudanças, confira se está editando `versoes/0.0.2/` e se
  nenhum arquivo privado foi incluído no envio.

## Convenção dos comentários

Os comentários usam o formato de cada arquivo: `<!-- ... -->` no HTML, `//`
no JavaScript, `#` no Python e `/* ... */` no CSS. Eles explicam o papel dos
blocos e a relação entre as camadas sem mudar o comportamento do site.
