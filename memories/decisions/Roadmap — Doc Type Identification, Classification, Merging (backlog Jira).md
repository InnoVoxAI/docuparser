---
title: Roadmap — Doc Type Identification, Classification, Merging (backlog Jira)
type: note
permalink: docuparser/decisions/roadmap-doc-type-identification-classification-merging-backlog-jira
tags:
- roadmap
- jira
- boleto
- plano-de-contas
- document-merging
---

## Contexto

Processo completo planejado pelo usuário (2026-09-21):

Doc upload → Doc Parsing → **Doc Type Identification** → **Doc Classification** →
**Document Merging** → Process Creation

Os dois primeiros já estão implementados. Os 3 seguintes foram transformados em
épicos de backlog (Jira) nesta sessão de planejamento (sem código ainda). CSV de
import gerado em `/tmp/.../scratchpad/docuparser-jira-import.csv` (efêmero — o
conteúdo completo dos tickets está replicado abaixo, não depender do CSV).

## EPIC 1 — Doc Type Identification: reconhecer boletos

**Descoberta importante**: já existe código parcial/órfão para boleto que
ninguém terminou de conectar:

- `backend-core/models/boleto/schemas.py` — heurística `is_likely()`/`score()`
  já usada por `ocr_processor._classify_raw_text()`
  (`backend-core/documents/services/ocr_processor.py:387-399`), com
  `SCHEMA_ID = "boleto_default"`.
- `langextract-service/domain/extractor.py` + `domain/schemas.py` —
  `SCHEMA_BY_LAYOUT` já mapeia `boleto_caixa`/`boleto_bb`/`boleto_bradesco` →
  schema `"boleto"`, com extrator regex funcional (`_extract_boleto`) pra
  linha_digitavel/vencimento/valor/beneficiario.
- **Falta**: não existe `models/boleto/definition.py` (só `nota_fiscal` e
  `contadeagua` têm — ver [[Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants]]),
  e `catalog/defaults.py::default_catalog_specs()` não inclui boleto. Resultado:
  `_classify_raw_text()` pode retornar `"boleto_default"`, mas
  `SchemaConfig.objects.filter(schema_id="boleto_default")` nunca encontra nada
  — a classificação morre silenciosamente, cai no fallback genérico.

Stories: (1) criar `models/boleto/definition.py` completo (shape igual a
`nota_fiscal/definition.py`: FIELDS, PROMPT_INSTRUCTIONS, EXAMPLES,
POST_PROCESSING, EXTRACTION_DEFINITION); (2) registrar no catálogo global
(`default_catalog_specs()` + migration de seed — **checar se
`catalog/0002_seed_default_catalog` já rodou em produção antes de mexer**);
(3) reconciliar/decidir o papel do extrator regex órfão do
langextract-service (legado a remover, ou fallback intencional?).

## EPIC 2 — Doc Classification: plano de contas

Não existe nenhum conceito de "plano de contas" no datamodel hoje —
`Document` (`backend-core/documents/models.py`) só tem `document_type`,
`layout`, `metadata` (JSON). É greenfield.

Regras de negócio definidas pelo usuário:
- CNPJ de concessionária (água/luz/gás) → Serviços Básicos
- INSS → Impostos
- RPA + dedetização → Serviços

Stories: (1) modelar plano de contas (decidir escopo global vs. por-tenant —
provavelmente por-tenant, ao contrário do catálogo de tipos que é global);
(2) motor de regras por CNPJ/natureza (fonte dos CNPJs de concessionária em
aberto — lista manual? CNAE/Receita Federal?); (3) persistir conta
classificada + `DocumentEvent` de auditoria; (4) tela de revisão/override
pelo operador.

## EPIC 3 — Document Merging: NF + boleto como processo de pagamento

Hoje "processo" na UI é 1:1 com `Document`
(`ProcessSummarySerializer` em `documents/serializers.py` deriva o processo
de um único Document — **não existe nenhum modelo de agrupamento**). Este
épico introduz esse conceito.

Regras de matching definidas pelo usuário:
- Mesmo CNPJ + valor bate → match
- Mesmo CNPJ, boleto de valor MENOR que a NF → match (N boletos por NF ok)
- Mesmo CNPJ, boleto de valor MAIOR que a NF → não faz match
- CNPJ diferente → não faz match
- Todo match (automático ou manual) exige confirmação humana antes de virar
  processo de pagamento.

Stories: (1) campo de rastreio de origem comum (`source_thread_id` + janela
de tempo — `Document` já tem `channel`/`correlation_id` mas não agrupamento
por conversa); (2) modelo `PaymentProcess` (ou similar) agrupando N
Documents; (3) algoritmo de matching CNPJ+valor; (4) fluxo de confirmação
obrigatória; (5) tela de match manual (fallback sem match automático).

## Process Creation

Marcado pelo usuário como "Para Futuro" — não detalhado. Depende do modelo
`PaymentProcess` do Epic 3.

## Relations

- relates_to [[Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants]]
