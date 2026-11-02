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

## UX para o analista (2026-10-26)

- **Fluxo guiado**: ao terminar uma sincronização iniciada na própria tela, redireciona sozinho
  para a confirmação (só se houver propostas; quem abre a tela depois não é redirecionado). A
  confirmação chega com um aviso do que veio e abre na primeira aba com pendências, na ordem
  plano, contas, condomínios. Confirmar o último plano avança sozinho para os condomínios.
- **Orientação**: resumo da última sincronização e do pendente por ação; aviso na aba de
  condomínios quando há plano pendente (sem o plano a confirmação é recusada); ponto e contagem
  no menu flutuante; guia de primeiros passos em Cadastros quando não há dados; Integrações
  aponta para Cadastros depois de salvar.
- **Volume (dezenas de condomínios)**: busca, "Confirmar todos (N)" por seção com diálogo de
  confirmação (o rótulo diz o escopo: todos, os filtrados, os desta página), cabeçalho fixo ao
  rolar, avisos do que foi confirmado, e estado final "Tudo confirmado" com atalho para Cadastros.
- **Armadilha corrigida**: logo depois de salvar as credenciais, Cadastros confiava no cache de
  5 s do overview e mantinha o botão de sincronizar bloqueado. O overview agora é relido toda
  vez que a tela abre, e a mensagem de credenciais não aparece enquanto ele carrega.
- Verificado no Chrome com uma fonte sintética (47 condomínios) num tenant temporário, removido
  depois; sem dados de cliente.

## Regras de fornecedor por plano e histórico do ERP (2026-11-02)

- **Contexto**: o plano é compartilhado por ~97 condomínios, então a regra de fornecedor por
  condomínio exigiria ~97 cópias. A API do Superlógica expõe despesas já lançadas
  (`despesas` com `idCondominio=-1`, `dtInicio` e `dtFim` ISO, paginada): cada uma traz o CNPJ/CPF
  de quem recebeu e a(s) conta(s) em `apropriacao`. Sem `idCondominio=-1` vem só um condomínio.
- **Modelo**: `SupplierRule` ganhou `chart`; `condominium` virou opcional e, quando preenchido,
  a regra vale só para ele e vence a do plano. Campos novos: `origin` (manual, history,
  learned), `evidence_count`, `evidence_total`, `alternatives`. As regras antigas ficaram como
  override por condomínio (o plano vem da conta). Migrations `accounting` 0007 a 0009.
- **Classificação**: busca regras do plano do condomínio e as só dele; override vence; com trecho
  vence sem trecho. Regra do histórico só pré-preenche com evidência: ao menos 2 lançamentos e
  90% de concordância (`SupplierRule.MIN_HISTORY_EVIDENCE` e `MIN_HISTORY_AGREEMENT`); as demais
  origens valem sempre. A razão registrada cita a evidência.
- **Semeadura**: `erp_import/history.py` e o comando `seed_supplier_rules --tenant <slug>
  [--months 24]` (somente leitura na fonte) criam ou atualizam uma regra por fornecedor e plano,
  com a conta mais usada. Idempotente, nunca sobrescreve regra manual ou aprendida, ignora conta
  não analítica ou de plano não importado. Aplicada direto, sem aprovação (decisão do usuário:
  regra só gera sugestão; o analista ainda confirma cada documento).
- **API**: `/charts-of-accounts/<id>/supplier-rules[/<id>]` para regras do plano; as rotas por
  condomínio continuam, para overrides.
- **Medido** (histórico de jan/2025 a out/2026, leave-one-out): sugerir sempre que o fornecedor
  é conhecido cobre 80% das despesas com 71% de acerto; com evidência clara (2 lançamentos e 90%)
  cobre 27% com 95% de acerto. 30% das despesas não têm CNPJ/CPF de fornecedor utilizável (folha,
  tributos): ficam para as regras de conteúdo.
- **Verificado**: importação real em tenant temporário, semeadura (754 regras de 2.408 despesas,
  160 confiáveis), idempotência, override, não sobrescrever manual, e cinco quebras propositais
  das regras novas, todas detectadas. Sem dados de cliente neste documento.

### Fases 3 a 6 (2026-11-02)

- **Limiar ajustado com dados**: teste temporal (aprende com o passado, testa nos últimos meses,
  `evaluate_history_rules`). Com 2 lançamentos e 90%: sugere em 22% das despesas e acerta 84%;
  com 3 lançamentos e 90%: 15% e 94%; com 4 e 100%: 12% e 97%. O leave-one-out anterior era
  otimista (95% com 2). Ficou em 3 lançamentos e 90% (`MIN_HISTORY_EVIDENCE = 3`): pré-preencher
  conta errada custa mais que não sugerir.
- **Regras por nome** (fase 6): despesa sem CNPJ/CPF utilizável mas com o nome de quem recebeu vira
  regra com `supplier_tax_id` vazio e o nome normalizado em `keyword` (8 a 64 caracteres; nome
  curto casaria com tudo). Casa por palavra inteira no texto do documento (`SupplierNameLookup`),
  logo depois da regra por CNPJ e antes das regras de conteúdo. No teste temporal: sugere em 32 a
  38% dessas despesas e acerta 94 a 95%. Despesas com nome usado uma vez só (a maioria) não aprendem.
- **Sugestões na tela** (fase 3): `GET /documents/<id>/account-suggestions` lista as contas que o
  fornecedor já usou, com `count` e `total`; o painel de classificação mostra "Usada em 49 de 68
  lançamentos" e deixa escolher. A mesma conta em várias regras fica com a maior evidência.
- **Aprendizado** (fase 4): `PUT .../ledger-account` aceita `remember`. Escolha avulsa soma
  evidência de peso 2 na regra do plano (origem `learned`, sujeita ao mesmo limiar); "Usar sempre"
  cria ou troca por regra `manual`, que vale sempre. Regra manual nunca é reescrita por escolha
  avulsa; a semeadura nunca sobrescreve regra manual nem aprendida. Aprovar o documento ainda não
  conta como evidência (possível melhoria).
- **Medição** (fase 5): `evaluate_history_rules --tenant <slug>` (teste temporal, só leitura) e
  `classification_report --tenant <slug>` (conta sugerida e mantida, trocada, escolhida sem
  sugestão, sem conta). Contra a planilha da Mariana: das 52 linhas com CNPJ/CPF, 45 têm regra, 8
  são claras o bastante para pré-preencher; as 4 com rótulo comparável concordam. 35 rótulos são
  grupos ou apelidos de pasta e não se comparam.
- **Atualização automática**: o fim de cada sincronização de cadastro bem-sucedida refaz as regras
  em segundo plano (falha só vai para o log). O comando também serve para agendar.
- **Anexos das despesas**: a API devolve só metadados (nome, hash, tamanho); os endpoints
  testados não entregam o arquivo, então não há conjunto de teste maior por aí.

### Tela de regras de fornecedor (2026-11-02)

- Página `/rules` no menu flutuante ("Regras de fornecedor"): por plano (o com mais condomínios vem
  escolhido), com busca (CNPJ, nome, código ou nome da conta), filtro de origem e de "pré-preenche",
  paginada de 50 em 50. Cada linha mostra fornecedor, conta, origem, evidência ("49 de 68, 72%") e
  se pré-preenche, com o motivo quando não pré-preenche. Ações (só `models.edit`): criar por CNPJ/CPF
  ou pelo nome no documento, trocar a conta, ativar ou desativar, excluir.
- API: `GET /charts-of-accounts/<id>/supplier-rules` agora devolve `{count, results}` com `search`,
  `origin`, `prefills`, `is_active`, `limit` e `offset`; cada regra traz a conta (`ledger_account`) e
  `prefills`. **Qualquer edição pela API torna a regra manual**, para a atualização do histórico não
  desfazer a decisão do analista. Excluir regra do histórico não adianta: ela volta na próxima
  atualização; para impedir, desativar.
- Armadilhas encontradas no navegador: no formulário de edição o fornecedor oculto ainda era
  validado e o botão Salvar não fazia nada (agora só valida ao criar); o aviso "Regra salva"
  continuava na tela depois de uma nova ação (agora some quando começa outra).

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
