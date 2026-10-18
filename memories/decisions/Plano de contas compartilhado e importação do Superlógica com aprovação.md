---
title: Plano de contas compartilhado e importação do Superlógica com aprovação
type: note
permalink: docuparser/decisions/plano-de-contas-compartilhado-e-importacao-do-superlogica-com-aprovacao
tags:
- plano-de-contas
- superlogica
- importacao
- datamodel
---

## Decisão

Épico 1 de `docs/pendencias-classificacao-plano-de-contas.md`, stories 1.1 a 1.3,
implementadas em 2026-10-17 e 2026-10-18 no `dev` local. Substitui a decisão de plano
**por condomínio** de [[docuparser/decisions/plano-de-contas-por-condominio-escopo-e-modelo]]:
no Superlógica o plano é compartilhado entre condomínios.

- **Story 1.1, `accounting.ChartOfAccounts`**: `LedgerAccount.chart` substitui
  `LedgerAccount.condominium`. Código e natureza são únicos por plano. `Condominium`
  ganhou `chart_of_accounts` (opcional) e `external_source`; `external_id` é único por
  fonte. Regra de fornecedor continua por condomínio, mas a conta precisa ser do plano do
  condomínio. Trocar o plano de um condomínio com regras de fornecedor é recusado.
- **Migração de dados**: cada condomínio que tinha contas virou dono de um plano só dele
  (sem deduplicar; unir planos é decisão posterior). `external_id` já preenchido recebeu
  `external_source="superlogica"`. A etapa de dados não tem volta.
- **API**: escrita de contas em `/charts-of-accounts[/<id>]` e
  `/charts-of-accounts/<id>/ledger-accounts[/<id>]`. `GET /condominiums/<id>/ledger-accounts`
  ficou só leitura (resolve pelo plano do condomínio) porque o painel de revisão o usa.
- **Classificação**: a conta de um documento perde a validade quando o novo condomínio tem
  outro plano; dois condomínios com o mesmo plano mantêm a conta.

## Importação (stories 1.2 e 1.3)

- `erp_import/sources/`: interface `RegistrySource` com objetos normalizados e cliente do
  Superlógica que só faz GET. Lê campos por lista de permitidos, então `st_token_emp` nunca
  sai do módulo. Mensagens de erro nunca trazem o corpo da resposta.
- `erp_import/planning.py` (funções puras) decide as propostas; `services.py` grava
  `ImportBatch` e `ImportProposal` e registra decisões. A sincronização não escreve em
  `Condominium`, `ChartOfAccounts` nem `LedgerAccount`.
- **Regras de conflito**: mesmo CNPJ, mesmo nome e endereço = um condomínio (fica o ativo,
  o outro vira `duplicate_external_ids`). Nomes ou endereços diferentes = conflito, todos
  entram sem CNPJ e o operador escolhe quem fica com ele (`resolve`). Se um registro já tem
  o CNPJ no cadastro, os outros entram sem CNPJ e sem novo conflito. CNPJ da administradora
  nunca vira CNPJ de condomínio (parâmetro `administrator_cnpj`, que a story 1.8 alimenta
  a partir da configuração do tenant). Cadastro local fora da fonte com o mesmo CNPJ vira
  conflito, nunca é ligado sozinho. CNPJ vazio na fonte nunca apaga o CNPJ local.
- Sumiu da fonte ou virou duplicado: proposta de desativar, nunca de apagar. Inativo
  desconhecido não entra. Natureza, regras de fornecedor e nomes alternativos nunca estão
  nas propostas.
- Plano novo leva as contas dentro da própria proposta; plano existente gera uma proposta
  por conta. Re-sincronizar sem mudanças não cria propostas; proposta pendente que mudou
  ou deixou de valer vira `superseded`.

## Pendências

- Story 1.4 aplica as decisões (hoje só são registradas, com autor e data) e cria a API
  e a execução em segundo plano. Ao aplicar: um plano novo precisa existir antes do
  condomínio que aponta para ele; desativar um duplicado que guarda o CNPJ esbarra na
  unicidade do CNPJ.
- Testes das stories 1.1 a 1.3 não foram escritos. Os 24 pontos de teste que criam
  `LedgerAccount(condominium=...)` precisam ser adaptados.
- Verificado em Postgres em 2026-10-18: a migração de dados sobre dados no formato antigo
  (contas, hierarquia, naturezas e regras de fornecedor preservadas, restrições novas
  valendo) e o serviço de sincronização (idempotência, nada gravado antes da aprovação,
  lote em erro sem propostas, decisões com autor e data). Por script avulso, não por teste.
- Na área tocada, 75 de 106 testes existentes falham até serem adaptados (story 1.9).

## Relations

- supersedes [[docuparser/decisions/plano-de-contas-por-condominio-escopo-e-modelo]]
- relates_to [[docuparser/reference/superlogica-api-condominios-fatos-verificados]]
