---
title: Wiki wagent - status dos milestones m1-m4 (2026-10-15)
type: note
permalink: docuparser/reference/wiki-wagent-status-dos-milestones-m1-m4-2026-10-15
tags:
- wagent
- wiki
- milestones
- roadmap
---

## Contexto

Em 2026-10-15 a wiki do projeto `docuparser` no wagent (4 milestones, 4 gates, todos abertos, nenhum documento) foi populada a partir do código.

## Status verificado no código

- **m1 Reconhecimento de boletos**: entregue e mergeado no `dev`. Wiki: ADR-001 (catálogo como única fonte de extração), feature `reconhecimento-e-extracao-de-boletos`, bugs `post-processing...nao-e-aplicado` e `classificador...primeiro-tipo-que-b`.
- **m2 Classificação em plano de contas**: backend nas branches empilhadas `022-chart-of-accounts` → `023-classification-rules` → `024-persist-classification`, NÃO mergeadas no `dev`; fora do pipeline (falta `Document.condominium`), sem telas. Wiki: ADR-002/003/004, EXP-001 (leave-one-out 95 docs), feature `classificacao-de-documentos-em-plano-de-contas-backend`, endpoint `PUT /documents/{id}/ledger-account`.
- **m3 Merge NF + boleto** e **m4 Telas de cadastro**: nenhum código encontrado (nenhum `PaymentProcess`, nenhuma tela de condomínio/conta/fornecedor no frontend). Não documentados.

## Pendências na wiki

- Quando a pilha 022-024 for mergeada ou o pipeline ligado, criar nova versão da feature m2 com `supersedes`.
- Quando o merge da 183242d chegar ao `dev`, publicar o bug do classificador como `resolvido` com `supersedes`.

## Relations

- relates_to [[docuparser/decisions/roadmap-doc-type-identification-classification-merging-backlog-jira]]
