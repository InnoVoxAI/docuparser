---
title: Revisão e override da conta classificada na tela de validação
type: note
permalink: docuparser/decisions/revisao-e-override-da-conta-classificada-na-tela-de-validacao
tags:
- doc-classification
- plano-de-contas
- frontend
- auditoria
---

## Decisão

Story "Tela de revisão/override de classificação pelo operador" (story 4 do épico
DOC-CLASSIFICATION-PDC), implementada em 2026-10-14 na branch `026-classification-review-ui`
(sai de `dev` local, que já tem as branches 022 a 025). Só a revisão da conta; as telas de
cadastro de condomínios, contas e fornecedores continuam sem existir (só API).

- **Onde**: painel `ClassificationReviewPanel` dentro de `ValidationDecisionPanel`
  (módulo `documents`), logo abaixo da origem do documento. Aparece em todo lugar que usa
  `ValidationView` (rota de validação e drawer da Visão Geral).
- **O que mostra**: condomínio, conta atual (código e nome), quem a definiu e por quê
  (`reason` do motor, ou o usuário quando foi manual). O operador troca por outra conta do
  plano do condomínio. Só contas ativas e sem filhas (analíticas) são oferecidas.
- **Sem condomínio**: o painel pede o condomínio (`PUT /documents/<id>/condominium`, que
  refaz a classificação). Com condomínio, "Alterar condomínio" permite corrigir uma
  identificação automática errada.
- **Tenant sem condomínios cadastrados**: o painel não aparece (não usa o plano de contas).
- **Auditoria**: o override usa `PUT /documents/<id>/ledger-account`, que já gravava o
  `DocumentEvent` `document.classified` com `classified_by` e conta anterior/nova
  (story 3). Esta story não mudou isso; só o consome.
- **Trava**: documento `APPROVED`, `REJECTED` ou em `ERP_*` não aceita mais troca de conta
  nem de condomínio (409 no backend, painel somente leitura no frontend). Critério do
  ticket: "antes de aprovar".

## Backend

- `GET /documents/<id>` ganhou `condominium` (`{id, name}`) e `classification`
  (`ledger_account {id, code, name}`, `origin`, `rule_id`, `reason`, `classified_by`,
  `updated_at`), com `select_related` para não gerar N+1.
- `DocumentClassificationSerializer` ganhou `ledger_account` aninhado.

## Frontend

- Dados em `useQuery`/`useMutation` (`useClassificationReview`), serviço em
  `services/classification.service.ts`, respostas validadas com zod na borda
  (`schemas/classification.ts`), formulário em React Hook Form + zod
  (`OptionPickerForm`, genérico para condomínio e conta). Regras puras em
  `classification.ts`.
- Os erros de validação do DRF vêm por campo (`ledger_account_id`); `readClassificationError`
  mostra a mensagem em vez do texto genérico.

## Limites

- Não há tela para ver o histórico (o histórico está nos `DocumentEvent`).
- Não foi verificado em navegador com a stack rodando, só em jsdom com MSW.
- O `Alert` compartilhado tem `mb-4`, então a mensagem de erro do formulário pode ficar
  com margem a mais.
- 16 testes de `flows`, `pagination` e `screens` já falhavam no `dev` antes desta mudança
  (mesma lista na base limpa e na branch).

## Relations

- part_of [[docuparser/decisions/roadmap-doc-type-identification-classification-merging-backlog-jira]]
- depends_on [[docuparser/decisions/persistencia-da-classificacao-em-conta-e-auditoria-por-document-event]]
- depends_on [[docuparser/decisions/identificacao-do-condominio-e-classificacao-ligada-ao-pipeline]]
