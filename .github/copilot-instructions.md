# Instrucoes do Copilot para o Site do Obito

- Antes de editar, confirme que o workspace e o clone `site-do-obito`. A versao principal do site esta na raiz; `old/` e historico.
- Leia o README da raiz para executar o projeto e escolher os testes apropriados.
- O VS Code pode estar aberto no clone local ou numa sessao remota de Live Share. Nunca diga que executou comandos no computador local se o terminal disponivel for remoto ou estiver indisponivel; explique a limitacao e forneca comandos para a pessoa executar localmente.
- A colaboracao usa GitHub Desktop para sincronizar. Nao execute `git push`, `git pull`, `git reset`, `git checkout` nem publique commits sem pedido explicito. Nao descarte alteracoes locais; deixe commit, push e pull para a pessoa no GitHub Desktop.
- Nunca leia em voz alta, copie, imprima ou inclua em respostas `.env`, tokens, senhas, connection strings, banco de dados ou uploads. Nao crie um `.env` real. Se for preciso verificar a configuracao, verifique somente se o arquivo existe, sem mostrar seu conteudo.
- Antes de instalar pacotes ou alterar o sistema, explique o que sera instalado e peça autorizacao. Use o PowerShell integrado somente quando ele estiver disponivel no computador local e a pessoa tiver autorizado a acao.
- Nao rode testes de autenticacao contra o banco de producao. `mvp-tattoo/test_auth.py` cria e apaga um schema temporario e requer uma base de testes dedicada.
- O Live Server serve arquivos estaticos; o site completo precisa do backend Flask. Consulte o README da raiz antes de iniciar o servidor.
- Faca alteracoes pequenas, explique em portugues o que mudou e informe quais validacoes foram realmente executadas.
