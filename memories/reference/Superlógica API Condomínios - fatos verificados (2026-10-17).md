---
title: Superlógica API Condomínios - fatos verificados (2026-10-17)
type: note
permalink: docuparser/reference/superlogica-api-condominios-fatos-verificados
tags:
- superlogica
- integracao
- plano-de-contas
- condominios
---

Fatos sobre a API, verificados em 2026-10-17 com chamadas GET reais (somente leitura) numa
licença de produção de um cliente. Só o comportamento da API fica aqui: nada de dados do
cliente, nem tokens. A pasta `documentation/` (outro dev) trata estes pontos como hipótese
[HIP]; abaixo estão os que viraram fato.

## Acesso

- Base `https://api.superlogica.net/v2/condor`. Bastam os headers `app_token` e
  `access_token`; o secret do app não foi necessário.
- Sem limite de taxa visível nos headers; cada página levou menos de 1 s.
- A resposta de condomínios traz um campo `st_token_emp` (um token). Não gravar o payload
  bruto em log, banco ou arquivo.

## Condomínios: `GET condominios/get`

- **Sem `id=-1` devolve só 1 condomínio** (o da licença). Para listar todos: `id=-1`,
  `itensPorPagina=50`, `pagina=N`. Página além do fim devolve lista vazia.
- A carteira de um cliente cabe em poucas páginas: a sincronização completa leva segundos.
- Campos úteis: `id_condominio_cond`, `st_nome_cond`, `fl_ativo_cond` (1 ou 0),
  `id_planoconta_plc`, `st_endereco_cond`, `st_cep_cond`, `st_cidade_cond`.
- **O CNPJ vem em `st_cpf_cond`** (nome enganoso). `st_cnpj_cond` veio vazio. Todos os
  registros tinham CNPJ de 14 dígitos válido.
- Há inativos, e o mesmo CNPJ aparece em mais de um registro: pares ativo e inativo (condomínio
  recadastrado) e também dois registros ativos com o mesmo CNPJ. Colide com a unicidade de
  CNPJ do `Condominium`. Há também nomes repetidos.

## Plano de contas: `GET planocontas`

- **O plano é compartilhado, não por condomínio.** O condomínio aponta para um plano por
  `id_planoconta_plc`, e quase todos os condomínios de um cliente usam o mesmo.
- `planocontas` sem parâmetro devolve o plano principal. `planocontas?id=<plano>` devolve as
  contas daquele plano. `planocontas?ID_PLANOCONTA_PLC=<qualquer>` devolve a lista de planos
  (um registro por plano).
- Conta: `st_conta_cont` (código pontuado), `st_descricao_cont` (nome), `st_ordenacao_cont`,
  `id_natureza_nat`, `id_planoconta_plc`. **A hierarquia está no código pontuado**: o pai de
  `2.1.10` é `2.1`. Não há campo de pai nem id próprio da conta.
- O primeiro nível separa receitas (grupo 1) de despesas (grupo 2). Um mesmo nome (ex. "Água")
  pode existir nos dois grupos, e um nome de despesa pode aparecer em dois lugares. As contas
  de INSS, FGTS, energia, gás e dedetização existem no plano padrão.

## Formato das respostas (verificado em 2026-10-18)

- As respostas são lista JSON pura, sem envelope. Todos os valores vêm como string,
  inclusive `fl_ativo_cond` ("1" ou "0") e os ids.
- Lista de planos (`planocontas?ID_PLANOCONTA_PLC=<qualquer>`): `id_planoconta_plc`,
  `st_nome_plc` (nome do plano) e `order_plano`.
- Condomínio: além dos campos acima, `st_numeroendereco_cond` e `st_bairro_cond` existem.
  O registro traz dezenas de campos de cobrança e contato que não são lidos.
- Conta: `st_conta_cont`, `st_descricao_cont`, `st_ordenacao_cont`, `id_natureza_nat`,
  `id_planoconta_plc`, mais campos contábeis não lidos.

## Não verificado

Fornecedores, despesas e escrita no ERP. O formato do campo de conta para lançar despesa
segue em aberto.

## Relations

- relates_to [[docuparser/decisions/plano-de-contas-por-condominio-escopo-e-modelo]]
- relates_to [[docuparser/reference/docs-por-plano-de-contas-dataset-de-documentos-reais]]
