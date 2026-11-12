---
title: Rastreio de origem comum dos documentos (source_thread_id)
type: note
permalink: docuparser/decisions/rastreio-de-origem-comum-dos-documentos-source-thread-id
tags:
- doc-merging
- ingestao
- datamodel
---

## Decisão

Story 1 do Epic 3 do [[Roadmap — Doc Type Identification, Classification, Merging (backlog Jira)]].

- **Campo**: `Document.source_thread_id` (texto, até 255, indexado, vazio por padrão), migration
  `documents/0019`. `correlation_id` não muda: ele continua sendo o id de rastreio de uma
  execução, enquanto a origem agrupa documentos que chegaram juntos.
- **Quem preenche** (backend-com, na ingestão, enviado no `document.received` como
  `data.source_thread_id`, opcional no contrato para eventos antigos continuarem válidos):
  - e-mail: `email:<Message-ID>`. Anexos do mesmo e-mail compartilham o valor. Se o e-mail
    não traz Message-ID fica vazio. No polling IMAP, sem o cabeçalho, entra o número da
    mensagem na caixa, que pode se repetir entre execuções.
  - WhatsApp: `whatsapp:<número de quem escreve>`. A conversa é o número; quem separa duas
    conversas do mesmo número é a janela de tempo.
  - upload manual: vazio (o canal não sabe a origem).
- **Janela de tempo**: `PAYMENT_MATCH_WINDOW_HOURS` (padrão 72, antes e depois de
  `received_at`), lida do ambiente em `core/settings.py`, documentada em `.env.example` e em
  `docs/TECHNICAL.md`. O valor de 72h continua sendo suposição a validar.
- **Uso**: a API devolve o campo na lista e no detalhe do documento. A busca de candidatos do
  matching continua pela janela, sem exigir a mesma origem, porque NF e boleto muitas vezes
  chegam em e-mails diferentes. A origem serve para o operador filtrar e agrupar.

## Relations

- relates_to [[docuparser/decisions/casamento-nf-e-boleto-por-cnpj-e-valor]]
