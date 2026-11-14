---
description: "Inspeciona e prepara o clone local do Site do Obito no VS Code sem expor segredos ou sincronizar Git automaticamente"
name: "Preparar Site do Obito (Muichi1)"
argument-hint: "Opcional: diga se quer apenas abrir o projeto, instalar dependencias ou iniciar o site"
agent: "agent"
---

Ajude a preparar e executar o Site do Obito neste VS Code.

1. Confirme se o workspace aberto e o clone GitHub Desktop `site-do-obito`. O caminho esperado neste computador e `D:\AsVeizDesenvolve\site-do-obito`. Se outro workspace estiver aberto, nao procure fora dele nem mude de pasta por conta propria; informe como abrir a pasta esperada no VS Code.
2. O codigo ativo do site fica na raiz do repositorio. Consulte `README.md` antes de decidir o que executar.
3. Use o terminal integrado apenas se uma ferramenta de terminal local estiver realmente disponivel. Se nao estiver, diga isso claramente e forneca comandos para a pessoa executar no PowerShell local. Uma sessao remota de Live Share nao e o PowerShell deste computador.
4. Primeiro inspecione se `py`/Python e as dependencias necessarias estao disponiveis. Nao instale programas ou pacotes sem explicar o que sera instalado e obter autorizacao.
5. Para iniciar o site completo, confirme apenas se `.env` na raiz existe; nao leia nem mostre seu conteudo. Se estiver ausente, nao o crie nem procure segredos em outro lugar. Explique que o backend precisa de configuracoes privadas e consulte o README para os proximos passos. Nunca compartilhe segredos no chat ou no Live Share.
6. Se as dependencias e configuracoes privadas estiverem prontas e houver autorizacao, execute `py app.py` com o diretorio de trabalho `mvp-tattoo`. Informe o endereco local mostrado pelo servidor. O Live Server nao substitui o backend Flask.
7. Nao execute `git pull`, `git push`, commits ou operacoes destrutivas. O GitHub Desktop controla a sincronizacao; nunca descarte alteracoes locais. Para baixar/enviar mudancas, oriente a pessoa a usar os botoes Fetch/Pull/Push do GitHub Desktop.
8. Nao execute `test_auth.py` contra producao. So rode esse teste se a pessoa confirmar que `DATABASE_URL` aponta para uma base de testes isolada.

No final, resuma o que verificou, o que iniciou e qualquer acao que dependa da pessoa. Nunca declare que algo foi instalado ou executado se nao tiver acesso real ao terminal local.
