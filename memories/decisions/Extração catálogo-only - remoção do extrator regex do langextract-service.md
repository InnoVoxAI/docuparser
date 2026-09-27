---
title: Extração catálogo-only - remoção do extrator regex do langextract-service
type: note
permalink: docuparser/decisions/extracao-catalogo-only-remocao-do-extrator-regex-do-langextract-service
tags:
- langextract-service
- boleto
- schema-config
- architecture
---

## Decisão (2026-09-27)

O catálogo global (`SchemaConfig.definition` via `LayoutConfig`) é a **única**
fonte de regras de extração. O extrator regex do langextract-service
(`domain/extractor.py`: `extract_fields`, `_extract_boleto`, `_extract_fatura`)
e o mapa fixo `SCHEMA_BY_LAYOUT` foram **removidos** (opção (a) do ticket
"Reconciliar extração de boleto entre langextract-service e catalog").

## Por que não era um fallback intencional

- `implementation-action-plan.md` (T-0401) o chama de "extrator
  deterministico" com pendência "substituir/adaptar para LLM quando o provedor
  for definido". O provedor (OpenRouter) foi definido.
- Não cobria falha do LLM: `extract_with_llm` devolve campos vazios quando a
  chamada falha, nunca cai no regex. O regex só rodava quando o worker não
  achava schema.
- Duplicava regras com nomes divergentes do catálogo (`schema_id` `boleto` /
  `fatura`, campos `vencimento`/`valor`/`beneficiario` vs `boleto_default`
  com `data_vencimento`/`valor_boleto`/`beneficiario_nome`).
- Os dois fluxos divergiam sem schema: o síncrono (backend-core) marca
  `pending_no_schema`; o assíncrono fabricava um resultado regex.

## Descoberta: o regex só rodava por bug

No fluxo assíncrono (`langextract-worker`), `domain/backend_core_client.py`
chamava `/api/ocr/layout-configs` sem `X-Tenant`; o `TenantMiddleware` do
backend-core rejeita token interno sem esse header (400
`SuspiciousOperation`), então **todo** lookup falhava e caía no regex.
Também não injetava `schema_id`/`version` na definition (o fluxo síncrono
injeta em `ocr_processor.py`), então o resultado LLM sairia como
`schema_id="generic"`.

## O que mudou

- `POST /api/v1/extract` exige `schema_definition` (422 sem ele). Único
  chamador em produção é `backend-core/documents/services/langextract_client.py`,
  que sempre envia.
- Worker: sem schema no catálogo, loga
  `langextract.extraction_skipped_no_schema` e **não publica**
  `extraction.completed` (espelha `pending_no_schema`; não vai pra DLQ porque o
  layout `generic` do layout-service é esperado e inundaria a DLQ).
- `backend_core_client` envia `X-Tenant` e marca a definition com
  `schema_id`/`version` do `SchemaConfig`.
- Testes do langextract usam LLM mockado (`extract_with_llm` e
  `fetch_schema_for_layout` via monkeypatch), como previa o T-0401.

## Consequências

- O smoke assíncrono com OCR mock descrito no action plan (resultado `boleto`,
  `valor=R$ 123,45`) não reproduz mais sem LLM: agora exige OpenRouter ou mock
  do `extract_with_llm`.
- O fluxo assíncrono continua quebrado **depois** do langextract, por bugs
  fora deste escopo: `backend-core-events` consome eventos sem
  `schema_context` do tenant (erro `relation "documents_documentevent" does
  not exist`) e não existe consumer de `layout.classified` que grave
  `Document.layout`. Ver [[Roadmap — Doc Type Identification, Classification, Merging (backlog Jira)]].

## Relations

- relates_to [[Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants]]
- relates_to [[Roadmap — Doc Type Identification, Classification, Merging (backlog Jira)]]
