---
title: Persistência da classificação em conta e auditoria por DocumentEvent
type: note
permalink: docuparser/decisions/persistencia-da-classificacao-em-conta-e-auditoria-por-document-event
tags:
- doc-classification
- plano-de-contas
- auditoria
- datamodel
---

## Decisão

Story "Persistir conta classificada e evento de auditoria" do épico
DOC-CLASSIFICATION-PDC, implementada em 2026-10-07 na branch `024-persist-classification`
(sai de `023-classification-rules`). Decidido com o usuário:

- **Estado atual em modelo relacionado no `accounting`**, não em campo do `Document`:
  `accounting.DocumentClassification` (OneToOne com `Document`, `ledger_account` com
  PROTECT, `origin` automatic/manual, `rule_id`, `reason`, `classified_by`). Assim o app
  `documents` continua sem depender do plano de contas.
- **Histórico só em `DocumentEvent`**, sem tabela de versões paralela. Cada classificação,
  automática ou manual, grava um `document.classified` (contrato novo em
  `contracts/events`, com exemplo e teste). O evento guarda a conta anterior e a nova com
  `id`, `code` e `name` copiados na hora, então o histórico continua legível se a conta for
  renomeada. É gravado direto no `DocumentEvent`, sem passar pelo barramento, porque
  nenhum outro serviço consome.
- **A escolha manual vence a automática.** `classify_document` nunca troca uma conta
  escolhida pelo operador: grava o evento com `applied=false` e a sugestão. Sem regra
  aplicável também grava evento (`applied=false`, conta vazia) e não muda o estado.

## Código

- `accounting/services.py`: `classify_document(document, condominium)`,
  `set_manual_classification(document, ledger_account, user)`, `facts_for_document`.
  Serializa classificações concorrentes com `select_for_update` no `Document`. Os fatos vêm
  da versão ativa dos campos (achatando `{value, confidence}`) e do texto bruto no storage.
- `PUT /api/ocr/documents/<id>/ledger-account` (permissão `documents.validate`), corpo
  `{"ledger_account_id": ...}`. Recusa conta inativa ou inexistente (400) e quem não é
  usuário (token de serviço, 403), porque a autoria precisa de alguém.
- Migration `accounting/0003_document_classification`.

## Limitações conhecidas

- **Não está ligado ao pipeline.** `classify_document` precisa do condomínio do documento,
  que ainda não existe. Ver a story "Identificar o condomínio de cada documento".
- A classificação manual não valida que a conta é do condomínio do documento, pelo mesmo
  motivo. Passa a validar quando `Document.condominium` existir.
- Não há endpoint de leitura do histórico nem da conta atual (story 4); o histórico está
  nos `DocumentEvent` com `event_type="document.classified"`.
- Reclassificação automática sem regra aplicável mantém a sugestão antiga (pode ficar
  desatualizada se o operador corrigir campos). O evento registra que nada foi aplicado.

## Relations

- part_of [[docuparser/decisions/roadmap-doc-type-identification-classification-merging-backlog-jira]]
- depends_on [[docuparser/decisions/motor-de-regras-de-classificacao-em-conta-fornecedor-e-conteudo]]
- depends_on [[docuparser/decisions/plano-de-contas-por-condominio-escopo-e-modelo]]
