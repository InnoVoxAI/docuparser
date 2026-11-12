---
title: Confirmação obrigatória do match de pagamento
type: note
permalink: docuparser/decisions/confirmacao-obrigatoria-do-match-de-pagamento
tags:
- doc-merging
- pagamento
- auditoria
---

## Decisão

Story 4 do Epic 3 do [[Roadmap — Doc Type Identification, Classification, Merging (backlog Jira)]].
Nenhum agrupamento vira processo de pagamento sem um operador confirmar.

- **Estado**: o `PaymentProcess` nasce `PENDING` e fica assim até alguém decidir (ver
  [[docuparser/decisions/processo-de-pagamento-agrupando-nf-e-boletos-paymentprocess]]).
- **API** (`documents.validate`, só usuário autenticado):
  `POST /api/ocr/payment-processes/<id>/confirm` e `.../reject`. Devolvem o processo com
  `decided_by` e `decided_at`. Erros: 409 `not_pending` (já decidido), 409 `boleto_taken` (algum
  boleto já foi confirmado em outra nota), 422 `no_boletos`.
- **Confirmar**: o processo vira `CONFIRMED`. Boletos que chegaram depois da primeira confirmação
  entram num pendente e, ao confirmar, são incorporados ao processo já confirmado da nota (o
  pendente é removido). Os boletos confirmados saem de qualquer outro pendente; pendente que fica
  vazio é apagado.
- **Rejeitar**: o processo vira `REJECTED` e fica como histórico. Os documentos voltam ao pool de
  documentos sem match, e o matching não sugere esse par de novo (a escolha manual pode).
- **Auditoria**: eventos `payment_process.confirmed` e `payment_process.rejected` (contrato em
  `contracts/events`, exemplos incluídos) gravados em `DocumentEvent`, um por documento do processo
  (nota e cada boleto), todos com o mesmo `data`: `process_id`, `origin`, `invoice_id`, `boleto_ids`
  e `decided_by`. O "quando" é o `occurred_at` do evento, igual ao `decided_at` do processo.
- **Tela** `/payments` (módulo `frontend/src/modules/payments`, item "Pagamentos" no menu com o
  número de pendentes): abas Para revisar, Confirmados e Rejeitados; cada agrupamento mostra nota,
  boletos, CNPJ, valor, origem (e-mail, WhatsApp ou envio manual) e quanto da nota os boletos
  cobrem. Confirmar e Rejeitar só aparecem com `documents.validate`; rejeitar pede confirmação.

## Relations

- relates_to [[docuparser/decisions/casamento-nf-e-boleto-por-cnpj-e-valor]]
