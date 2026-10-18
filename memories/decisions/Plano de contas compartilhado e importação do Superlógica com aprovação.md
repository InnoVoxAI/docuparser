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

## Aplicação, API e telas (2026-10-18)

- Decidir aplica a mudança na mesma transação (`erp_import/apply.py`); repetir a decisão é
  um no-op. Status finais: aprovada, conflito resolvido, rejeitada, substituída. Plano antes de
  conta e de condomínio; o lote ordena, a aprovação isolada recusa com mensagem.
- Rejeição lembrada pela assinatura da proposta (ação, dados, diferenças, avisos): volta só se
  a fonte mudar. "Nenhum fica com o CNPJ" é lembrado por CNPJ e conjunto de registros; sem
  isso o mesmo conflito voltava a cada sincronização (achado na rodada com dados reais).
- A escolha de CNPJ resolve o grupo todo. Ligar a um cadastro local reaponta o `external_id`
  do cadastro local; "é outro condomínio" importa sem CNPJ.
- Sincronização em segundo plano (`ThreadPoolExecutor` de 1 worker, como o processamento de
  documentos), um lote por vez; lote parado há mais de 15 minutos é encerrado como erro.
- Tokens: Fernet com `DOCUPARSE_SECRETS_KEY` (obrigatória para salvar tokens), por tenant, na
  `IntegrationSettings`. Nunca saem pela API. Sem fallback para tokens de ambiente: um token
  do ambiente serviria a todos os tenants.
- Frontend: módulo `registry` (listagem, sincronizar, cadastro manual, confirmação) e campos de
  credenciais em Configurações > Integrações. Edição de nomes alternativos, naturezas e
  fornecedores, e as listas de documentos com condomínio e conta, ficaram adiadas.

## Pendências

- Identificação de documentos ignorar o CNPJ da administradora (resto da story 1.8).
- Desativar um duplicado que guarda o CNPJ: o registro desativado mantém o CNPJ.
- Adaptar os testes antigos de `accounting`, `condominiums` e do pipeline ao plano
  compartilhado (75 de 106 falham) e fixar testes do planejador e do cliente do Superlógica.
- Ver as telas num navegador com a stack rodando.
- Verificado em Postgres: migração de dados sobre dados no formato antigo, serviço de
  sincronização, API e uma rodada completa contra o Superlógica real (somente leitura).

## Relations

- supersedes [[docuparser/decisions/plano-de-contas-por-condominio-escopo-e-modelo]]
- relates_to [[docuparser/reference/superlogica-api-condominios-fatos-verificados]]
