---
title: Plano de contas por condomínio (escopo e modelo)
type: note
permalink: docuparser/decisions/plano-de-contas-por-condominio-escopo-e-modelo
tags:
- doc-classification
- plano-de-contas
- multi-tenancy
- datamodel
---

## Decisão

> Atualização (2026-10-18): o plano passou a ser **compartilhado** entre condomínios, como no
> Superlógica. Ver [[docuparser/decisions/plano-de-contas-compartilhado-e-importacao-do-superlogica-com-aprovacao]].
> O texto abaixo descreve o modelo original.

O plano de contas é **por condomínio**, com as tabelas no schema de cada tenant.
Story "Modelar Plano de Contas" do épico DOC-CLASSIFICATION-PDC, decidida em
2026-09-30 (branch `022-chart-of-accounts`).

## Por quê

- O plano de contas existe para lançar a despesa no ERP do cliente (Superlógica).
  A conta classificada precisa bater com a conta que já existe no ERP daquele
  cliente. Um plano global, como o catálogo de tipos de documento
  ([[Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants]]),
  não serviria a nenhum cliente.
- Tenant = administradora, que gerencia N condomínios (o pagador dos boletos e NFs
  é o condomínio). No ERP de condomínio, cada condomínio tem o próprio plano,
  em geral copiado de um padrão da administradora. Um plano por tenant misturaria
  condomínios.
- No schema do tenant as tabelas não precisam de `tenant_id`: o schema já isola.
  A futura FK `Document → LedgerAccount` fica no mesmo schema.
- Tenant novo começa sem condomínios e sem contas. Não há seed, então não há passo
  de provisionamento que possa falhar (a classe de bug eliminada na spec 018).

Alternativas descartadas: plano global em `public`; plano por tenant sem
condomínio; template global copiado para cada tenant (reintroduz provisionamento,
pode voltar como follow-up "copiar plano").

## Modelo

- App `condominiums` (TENANT_APPS): `Condominium` com `name`, `cnpj` (opcional,
  único quando preenchido, gravado sem pontuação, aceita o CNPJ alfanumérico e
  valida os dígitos verificadores), `external_id` (id no Superlógica), `is_active`.
  É um app próprio porque outros épicos (merge NF + boleto por CNPJ, roteamento)
  também vão usar o condomínio.
- App `accounting` (TENANT_APPS): `LedgerAccount` com `condominium` (FK, PROTECT),
  `parent` (FK para si mesma, PROTECT), `code` (código no ERP, único por
  condomínio), `name`, `is_active`. Conta sem filhas é analítica (não é campo).
  Pai no mesmo condomínio e ausência de ciclo são validados no serializer.
  O nome é `LedgerAccount`, e não `Account`, para não confundir com conta de
  login nem com a conta bancária que aparece nos boletos.
- Na story do motor de regras (2026-10-04) o `LedgerAccount` ganhou `nature`
  (opcional, única por condomínio) e surgiu o cadastro `SupplierRule`. Ver
  [[docuparser/decisions/motor-de-regras-de-classificacao-em-conta-fornecedor-e-conteudo]].

## API

- `/api/ocr/condominiums` (GET, POST) e `/api/ocr/condominiums/<id>` (GET, PATCH,
  DELETE; 409 se o condomínio tiver contas).
- `/api/ocr/condominiums/<id>/ledger-accounts` (GET em lista plana ordenada por
  `code`, POST) e `/api/ocr/condominiums/<id>/ledger-accounts/<id>` (GET, PATCH,
  DELETE; 409 se a conta tiver filhas).
- Permissão: leitura `inbox.view`, escrita `models.edit` (mesmo gate das
  configurações do tenant), via `users.permissions.require_permission_by_method`.
  Nenhuma permissão nova, então não há data migration em `users`.
- CRUD via API e não via admin: o Django admin roda no schema `public` e não
  enxerga tabelas de tenant.

## Pendências

- Story nova sugerida no épico: identificar o condomínio de cada documento (CNPJ
  do pagador ou do tomador), com FK `Document.condominium`. Sem isso o motor de
  regras não sabe de qual plano escolher a conta.
- Copiar o plano entre condomínios ou importar do Superlógica: cadastro manual
  não escala.
- Story 2 (motor de regras, só conta analítica), story 3 (FK
  `Document.ledger_account` e `DocumentEvent`), story 4 (telas).

## Status

Implementado na branch `022-chart-of-accounts` em 2026-09-30.
17 testes novos em `condominiums/tests` e `accounting/tests`.

## Relations

- part_of [[docuparser/decisions/roadmap-doc-type-identification-classification-merging-backlog-jira]]
- contrasts_with [[Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants]]
