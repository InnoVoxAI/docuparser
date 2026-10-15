---
name: wagent-docs
description: Use quando o trabalho num projeto de P&D da InnoVox produzir algo que vale registrar na wiki (decisão de arquitetura, experimento com resultado, feature entregue, endpoint/tabela/bug/termo) ou quando o usuário pedir para documentar. Orienta o julgamento sobre O QUE e QUANDO publicar com o MCP wagent; as regras de estrutura são aplicadas pelo servidor.
---

# Documentar no Wiki.js com o MCP wagent

O servidor `wagent` aplica as regras de estrutura (caminho, numeração, tamanhos, segredos,
duplicidade) e devolve erros `{code, message, hint}`: siga o `hint`. Esta skill cobre só o
**julgamento**. O detalhe de cada campo está na descrição de cada tool e em
`get_project_context` (`templates` e `rules`); não o decore, leia de lá.

## Quando documentar

Só o que tem valor duradouro para outras pessoas:

| Situação | Tool |
|---|---|
| Decisão de arquitetura **já tomada**, com alternativas descartadas | `create_adr` |
| Experimento **com resultado** (inclusive negativo, inconclusivo ou abandonado) | `create_experiment` |
| Feature entregue ou alterada de forma relevante | `create_feature` |
| Endpoint, tabela, bug conhecido ou termo novo ou alterado | `create_reference` |

`create_gate_summary` só quando o usuário pedir: o resumo nasce `[UNDER REVIEW]` e quem
confirma é uma pessoa admin (`confirm_gate`), nunca você.

## Quando NÃO documentar

Progresso trivial, tentativas intermediárias, planos e dúvidas, logs, conversa, e tudo o que
já está no Jira ou no Git. Na dúvida, pergunte ao usuário antes de publicar: a wiki é só de
criação, e um documento errado não pode ser editado nem apagado por você.

## Fluxo

1. `get_project_context(project)`: confirme o projeto, o gate e o milestone atuais e leia
   `rules`. Se o projeto não existir, o `hint` lista os válidos (`list_projects`). Se não houver
   milestone atual, o `hint` diz o que fazer; não invente um.
2. `search_docs(query, project=...)`: o assunto já existe? Se sim, **não duplique**: crie uma
   nova versão com `supersedes` (veja abaixo). Se for só consulta, `get_doc(path)` lê o conteúdo.
3. `create_*(project, document, acknowledge_similar)`: `document` leva os campos do tipo
   (`title`, `agent_name`, ...). Envie sempre `client_request_id` (um retry não duplica).
   Nunca informe caminho: o servidor o calcula.
4. Informe ao usuário o `url` retornado. Se `index_updated` vier `false`, o documento
   **existe** (só o índice falhou): não recrie, apenas avise.

## `supersedes`: atualizar é criar uma nova versão

Documentos existentes não são editados. Para corrigir ou evoluir algo já publicado (ADR
revertido, feature v2, bug resolvido, endpoint que mudou), crie um documento novo com
`supersedes` = `path` do antigo (obtido em `search_docs`). O alvo precisa ser do mesmo tipo (e,
em referências, do mesmo `kind`) e ainda não substituído. O servidor marca o antigo como
`substituida` e liga os dois.

## `POSSIBLE_DUPLICATE`

O servidor achou documentos parecidos. Não reenvie no automático:

1. Leia os candidatos do `hint` com `get_doc`.
2. Se é o mesmo assunto: descarte o novo ou, se traz informação nova, recrie com `supersedes`
   apontando para o candidato.
3. Só se for realmente um documento **distinto**, reenvie a mesma chamada com
   `acknowledge_similar=[paths dos candidatos que você leu]`.

## `RATE_LIMITED`

Há um limite de criações por token por hora (freio contra loops). Ao receber `RATE_LIMITED`,
**pare de criar**: não tente de novo em laço. Documente o essencial num único documento
maior ou aguarde o tempo indicado no `hint`.

## Nunca incluir

Credenciais, tokens, chaves, dados pessoais ou de clientes (o servidor rejeita padrões
conhecidos com `SECRET_DETECTED`, mas não pega tudo). Se o conteúdo for sensível, resuma e
referencie a fonte. Se receber `SECRET_DETECTED`, remova o trecho; não tente disfarçá-lo.

## Como escrever

Em português, direto, com contexto suficiente para quem chega sem conhecer o projeto. Links
para tickets Jira (`PROJ-123`, no campo `jira`). Dados e números com a fonte. `agent_name` é o
seu nome de agente, não o do usuário.

## Fora do seu alcance

Registrar projetos, abrir/fechar gates e milestones, confirmar gates e emitir tokens são
tools de **admin**, para pessoas; `bootstrap_admin` nunca deve ser chamada por agente. Se
receber `FORBIDDEN`, peça ao usuário que acione um admin.
