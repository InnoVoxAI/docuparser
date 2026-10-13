---
title: Identificação do condomínio e classificação ligada ao pipeline
type: note
permalink: docuparser/decisions/identificacao-do-condominio-e-classificacao-ligada-ao-pipeline
tags:
- doc-classification
- plano-de-contas
- pipeline
- datamodel
---

## Decisão

Story "Identificar o condomínio de cada documento" (texto escrito em 2026-10-07, ainda
sem ticket no Jira) implementada junto com a ligação do motor ao pipeline, na branch
`025-identify-condominium` (sai de `024-persist-classification`), por pedido do usuário
("já ligue o pipeline"). Sem a identificação o motor não tem plano de contas para usar.

- **`Document.condominium`**: FK opcional para `condominiums.Condominium` (PROTECT),
  migration `documents/0016`. Foi escolhida FK direta no `Document` (e não modelo
  relacionado como na classificação) porque o condomínio é a identidade do documento e
  outros épicos (merge NF + boleto por CNPJ, roteamento) vão filtrar por ele.
  Consequência: `documents` passa a depender de `condominiums` e chama `accounting`
  nos pontos do pipeline.
- **Identificação automática** (`accounting/classification/identification.py`), em ordem:
  CNPJ do pagador extraído (`cnpj_cpf_pagador`, `cnpj_tomador`), CNPJ de condomínio no
  texto bruto, nome ou nome alternativo no texto (vence o trecho mais longo). Ambíguo
  vira "não identificado"; nunca adivinha. Só considera condomínios ativos.
- **Nomes alternativos**: `Condominium.aliases` (lista JSON, migration
  `condominiums/0002`), validada no serializer (sem vazios, sem duplicatas, e um nome
  não pode identificar dois condomínios). `normalize_text` foi para `condominiums/text.py`.
- **Só preenche o que está vazio**: a identificação automática nunca troca um condomínio
  já definido (do operador ou de execução anterior). Não há campo de "origem".
- **Tenant sem condomínios ativos** não usa o plano de contas: nada é feito nem
  registrado, então o comportamento dos clientes atuais não muda.
- **Eventos**: `document.condominium_identified` (contrato novo em `contracts/events`)
  a cada tentativa, automática ou manual, com método, condomínio anterior e novo.
- **Operador**: `PUT /api/ocr/documents/<id>/condominium` (`documents.validate`, só
  usuário autenticado). Grava o evento e refaz a classificação no novo condomínio.
- **Conta de outro condomínio**: se o documento troca de condomínio, a conta vigente deixa
  de valer. `classify_document` a substitui pela do novo plano ou a remove (evento com
  `applied=true`, `ledger_account` vazio e a conta anterior). Resolve o ponto em aberto
  da story.
- **Conta manual** (`PUT .../ledger-account`) agora exige o condomínio do documento e que
  a conta seja dele (fecha a limitação anotada em
  [[docuparser/decisions/persistencia-da-classificacao-em-conta-e-auditoria-por-document-event]]).

## Ligação ao pipeline

`accounting.services.run_classification_safely(document)` (identifica se faltar, classifica
e nunca levanta exceção) é chamado em:

1. `auto_extract_after_ocr`, no caminho de sucesso (depois do `try/except` que relança);
2. `auto_extract_after_ocr`, quando não há schema (só texto bruto: recibo de pessoa
   física, por exemplo);
3. `run_langextract_for_document` (extração manual);
4. `consume_extraction_completed`, depois de fechar a transação do evento.

## Não ligado

- Edição manual de campos (`document_save_fields_view`): corrigir o CNPJ do pagador não
  refaz a identificação nem a classificação.
- `DOCUPARSE_AUTO_PROCESS_EXTRACTION=false` e documento sem texto bruto: o caminho
  automático retorna antes.
- Nada lê o condomínio ou a conta na API de documentos (story 4); o ERP ainda não recebe o
  código da conta.

## Armadilha de teste

Teste Postgres/tenant que falha com `DoesNotExist` vindo de `.get()` derruba os testes
seguintes da classe no modo de traceback padrão: o pytest exibe os argumentos do frame,
o `repr` do `QuerySet` consulta o banco com o schema já revertido e aborta a transação.
Nos testes novos, usar `.filter().first()` nas asserções.

## Relations

- part_of [[docuparser/decisions/roadmap-doc-type-identification-classification-merging-backlog-jira]]
- depends_on [[docuparser/decisions/motor-de-regras-de-classificacao-em-conta-fornecedor-e-conteudo]]
- depends_on [[docuparser/decisions/persistencia-da-classificacao-em-conta-e-auditoria-por-document-event]]
