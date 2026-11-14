# Para abrir e trabalhar no VS Code da Muichi1

Este arquivo aparece na raiz do clone sincronizado pelo GitHub Desktop:

```text
D:\AsVeizDesenvolve\site-do-obito
```

## Abrir o projeto certo

1. Abra essa pasta no VS Code: **File > Open Folder...**
2. Trabalhe diretamente na raiz do clone: a versao principal agora fica nela.
3. Confirme a instalacao das extensoes recomendadas se o VS Code oferecer.
4. Abra o Copilot Chat no modo **Agent** e selecione o prompt
   **Preparar Site do Obito (Muichi1)** (ou digite `/` e procure esse nome).
   Ele inspeciona o ambiente e orienta como iniciar o site sem mostrar segredos.

As instrucoes gerais do projeto estao em `.github\copilot-instructions.md`;
elas sao carregadas automaticamente pelo Copilot Chat compatível com
custom instructions.

## Live Share e GitHub Desktop sao coisas diferentes

- **Live Share** permite editar/juntar-se a uma sessao em tempo real. O terminal
  de uma sessao remota nao controla o PowerShell local da Muichi1.
- **GitHub Desktop** baixa e envia commits do repositorio entre os computadores.
  Depois de alguem enviar mudancas ao GitHub, a outra pessoa usa **Fetch origin**
  e **Pull origin** no GitHub Desktop para baixá-las.
- As alteracoes locais nao sao enviadas automaticamente. Revise as mudancas,
  faca commit e use **Push origin** no GitHub Desktop quando estiver pronta.
- Trabalhem em branches separadas quando possivel e usem Pull Request para
  revisar antes de integrar na branch `main`.

## Para executar o site

O Live Server mostra paginas estaticas, mas nao executa as APIs do backend.
Para o site completo, o computador precisa de Python, dependencias e
configuracao privada do banco/servidor. Abra `README.md` e use o prompt do
Copilot para verificar o que ja esta pronto.

Nunca sincronizem ou compartilhem `.env`, senhas, tokens, banco local ou
arquivos enviados por clientes. O Copilot nao deve criar um `.env` verdadeiro
nem imprimir seu conteudo no chat.
