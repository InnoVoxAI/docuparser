---
title: Processo de pagamento agrupando NF e boletos (PaymentProcess)
type: note
permalink: docuparser/decisions/processo-de-pagamento-agrupando-nf-e-boletos-paymentprocess
tags:
- doc-merging
- pagamento
- datamodel
---

## Decisão

Story 2 do Epic 3 do [[Roadmap — Doc Type Identification, Classification, Merging (backlog Jira)]].

- **Modelo** `documents.PaymentProcess` (migration `0020`): `invoice` (FK para a nota),
  `boletos` (M2M para `Document`), `status` (`PENDING`, `CONFIRMED`, `REJECTED`), `origin`
  (`AUTOMATIC`, `MANUAL`), `decided_by` e `decided_at`. Substitui o `PaymentMatch`, que era um
  par por linha: o sugerido e o confirmado são o mesmo registro, mudando só o status, para
  não haver duas fontes da verdade.
- **Restrições no banco**: no máximo um processo `PENDING` e um `CONFIRMED` por nota; rejeitados
  podem repetir (ficam como histórico e impedem que o mesmo par volte a ser sugerido).
- **Boleto novo para nota já confirmada**: abre um pendente só com o boleto novo. Na confirmação
  ele é incorporado ao confirmado (story 4).
- **Um boleto pode estar em vários pendentes** (duas notas de mesmo CNPJ e valor); só um
  confirmado. Boleto confirmado em outra nota não é mais sugerido.
- **Sem match, nada muda**: documento fora de processo segue avulso; a lista de processos e o
  detalhe do documento trazem `payment_processes: []`. Apagar o último boleto de um pendente
  apaga o processo vazio (`post_delete` em `documents/signals.py`).
- **API de leitura** (`inbox.view`): `GET /api/ocr/payment-processes` (paginada, filtros `status`,
  `origin`, `document_id`) e `GET /api/ocr/payment-processes/<id>`. Cada processo traz nota e
  boletos com `tax_id` e `amount` lidos dos campos vigentes, `invoice_amount` e `boletos_total`.
  `payment_processes` (id, status, papel `invoice` ou `boleto`) entra no detalhe do documento e
  na linha do dashboard de processos; rejeitados não aparecem ali.
- Valores não são gravados no processo: saem dos campos vigentes na hora de ler, então a edição
  do operador aparece.

## Relations

- relates_to [[docuparser/decisions/casamento-nf-e-boleto-por-cnpj-e-valor]]
- relates_to [[docuparser/decisions/rastreio-de-origem-comum-dos-documentos-source-thread-id]]
