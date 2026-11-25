---
title: Pareamento manual de NF e boleto (documentos sem match)
type: note
permalink: docuparser/decisions/pareamento-manual-de-nf-e-boleto-documentos-sem-match
tags:
- doc-merging
- pagamento
- frontend
---

## Decisão

Story 5 do Epic 3 do [[Roadmap — Doc Type Identification, Classification, Merging (backlog Jira)]]:
fallback quando o matching automático não casa. Reaproveita o fluxo de
[[docuparser/decisions/confirmacao-obrigatoria-do-match-de-pagamento]].

- **Pool de sem match** (`GET /api/ocr/payment-candidates?kind=invoice|boleto&search=`, `inbox.view`):
  documentos do tipo que não estão em nenhum processo `PENDING` ou `CONFIRMED`, nem rejeitados.
  O tipo vem dos campos que o schema extrai (`cnpj_fornecedor`/`valor_nota` para nota,
  `cnpj_cpf_beneficiario`/`valor_boleto`/`valor_documento` para boleto), mesmo quando o valor não
  foi lido: um boleto cujo CNPJ o OCR cortou segue sendo boleto e aparece aqui, que é justamente o
  caso do pareamento manual. A busca é a mesma da caixa de entrada (nome, tipo, canal e campos).
  Documentos de um agrupamento rejeitado voltam para o pool.
- **Montar o par** (`POST /payment-processes/manual`, `documents.validate`, corpo
  `{invoice_id, boleto_ids}`): cria um `PaymentProcess` `PENDING` com `origin=MANUAL`. Não exige
  CNPJ nem valor iguais; a tela avisa (CNPJ diferente, CNPJ ou valor não lido, boleto ou soma acima
  da nota). Erros: 400 `wrong_kind`, 404 `not_found`, 422 `no_boletos`, 409 `invoice_busy` (a nota
  já tem agrupamento pendente) e `boleto_unavailable` (boleto já pendente ou confirmado).
- **Desfazer** (`POST /payment-processes/<id>/undo`): só para manual ainda pendente; apaga o
  processo e os documentos voltam ao pool. Para sugestão automática o caminho é rejeitar (409
  `not_manual`); confirmado não se desfaz (409 `not_pending`). Antes de montar, "Desfazer seleção"
  na tela só limpa a escolha, sem chamar a API.
- **Depois de montado** o agrupamento aparece em "Para revisar" com origem "Montado à mão" e
  "Desfazer seleção" no lugar de "Rejeitar"; confirmar grava o evento com `origin: manual`.
- **Tela**: aba "Sem match" em `/payments`, com as notas (escolha única) e os boletos (escolha
  múltipla) lado a lado, cada coluna com busca e paginação, e a barra de seleção. Quem só tem
  `inbox.view` vê as listas, sem a barra. Quem quer ver o que já tem match usa as abas Confirmados
  e Para revisar.

## Limites

- Um documento que está em sugestão automática pendente não aparece no pool: é preciso rejeitar a
  sugestão antes de pareá-lo de outro jeito.
- Não há evento de auditoria para "montou" ou "desfez"; só a decisão final é gravada.

## Popup de documentos lado a lado (2026-11-25)

O analista não via nada além de nome, CNPJ e valor. O botão "Ver documentos" de cada
agrupamento, o nome de cada documento e o botão de olho da lista de "Sem match" abrem um
popup em `modules/payments/components/DocumentCompareDialog.tsx`:

- **Conferência no topo** (`compareChecks.ts`): CNPJ do fornecedor, valor coberto ou faltando,
  **pagador do boleto = tomador da nota** (pega boleto de outro condomínio, que a regra de
  casamento não checa), vencimentos em ordem, origem comum e condomínio com a conta.
- **Nota à esquerda, boleto à direita** (abas quando há vários boletos), cada um com os campos
  que decidem e o arquivo original (`DocumentBlobPreview`). Campos opcionais não lidos ficam
  recolhidos para o PDF ter espaço.
- **Decisão sem sair do popup:** confirmar e rejeitar no rodapé, ou "Montar agrupamento" na
  seleção manual. Se montar falha, o popup fecha para o erro aparecer na barra.
- Os dados vêm de `GET /documents/{id}` (`extraction_result` já reflete a versão ativa dos campos)
  e `/documents/{id}/file`, sem endpoint novo no backend.
- Verificado no navegador real (Chrome, core local) com PDFs reais: layout, abas, Escape, seleção
  manual e documento único.

## Relations

- relates_to [[docuparser/decisions/processo-de-pagamento-agrupando-nf-e-boletos-paymentprocess]]
