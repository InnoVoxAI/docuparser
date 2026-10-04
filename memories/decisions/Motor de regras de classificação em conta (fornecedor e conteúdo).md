---
title: Motor de regras de classificação em conta (fornecedor e conteúdo)
type: note
permalink: docuparser/decisions/motor-de-regras-de-classificacao-em-conta-fornecedor-e-conteudo
tags:
- doc-classification
- plano-de-contas
- regras-de-negocio
---

## Decisão

Story "Motor de regras de classificação por CNPJ/natureza" do épico
DOC-CLASSIFICATION-PDC, implementada em 2026-10-04 na branch
`023-classification-rules` (sai de `022-chart-of-accounts`). Desenho baseado nos
documentos reais de [[docuparser/reference/docs-por-plano-de-contas-dataset-de-documentos-reais]].

- **Sinal principal: CNPJ ou CPF de quem cobra**, num cadastro de fornecedores **por
  condomínio** (`accounting.SupplierRule`: condomínio, `supplier_tax_id`, `keyword`
  opcional, `ledger_account`). A `keyword` separa cobranças diferentes do mesmo
  fornecedor (sindicato: "MEN" mensalidade vs. "CAS" contribuição assistencial).
- **Fonte dos CNPJs de concessionárias: lista mantida pelo operador** (o próprio
  cadastro de fornecedores). CNAE/Receita foi descartado porque os dados reais não
  batem: o gás da cliente é de distribuidora de botijão (Bahiana), não concessionária,
  e a conta "Água" recebe manutenção e saneantes.
- **Regras de conteúdo** (em código) para documentos sem fornecedor útil: DARF/GPS
  previdenciário vai para a natureza `inss`, guia do FGTS para `fgts`, recibo de pessoa
  física sem cadastro (ex. RPA) para `servico_pessoa_fisica`. Recibo de pensão fica de
  fora. A conta de cada natureza é a do condomínio marcada em `LedgerAccount.nature`
  (opcional, única por condomínio); sem conta marcada, o documento fica sem sugestão.
- **Ordem**: cadastro de fornecedores primeiro (decisão explícita do operador), depois
  as regras de conteúdo. A primeira que achar conta vence.
- O mesmo modelo de recibo aparece em contas diferentes (gerente em Prestação PF,
  eletricista em Manutenções, pensão em Alimentação): por isso o cadastro aceita CPF e
  a regra de recibo é só o fallback.

## Código

- `accounting/classification/`: `classify(facts, condominium, rules=RULES)`,
  `DocumentFacts(fields, raw_text)`, `Classification(ledger_account, rule_id, reason)`.
  Regra nova = classe com `rule_id` e `apply(facts, condominium)`, acrescentada a
  `RULES` em `rules.py`. Regras de conteúdo herdam de `NatureRule`.
- `DocumentFacts.supplier_tax_id` lê `cnpj_cpf_beneficiario` (boleto),
  `cnpj_fornecedor` (NF) ou `cnpj_emissor` (conta de consumo), ignorando o CNPJ do
  condomínio. No texto bruto só aceita candidato único, porque boletos de
  intermediários (Cora, Safe2Pay) trazem mais de um CNPJ.
- `condominiums/tax_ids.py`: validação de CNPJ (inclusive alfanumérico) e CPF.
- API: `/api/ocr/condominiums/<id>/supplier-rules[/<id>]`, mesmas permissões do plano
  de contas; `nature` no serializer de `LedgerAccount`.

## Avaliação no dataset (2026-10-04)

Leave-one-out sobre os 95 documentos, só com texto bruto (piso: produção tem os campos
extraídos): 44 certos, 1 errado (sindicato sem keyword), 50 sem sugestão (25 sem
CNPJ/CPF de terceiro, 6 com mais de um candidato no texto, 15 de fornecedor visto uma
vez só). Script fora do repo, porque o dataset tem dados pessoais.

## Pendências

- O motor não está ligado ao pipeline: depende de identificar o condomínio do
  documento (story nova) e de persistir a conta (story 3).
- RPA: a cliente não confirmou o formato. A regra cobre recibo de pessoa física; outro
  formato vira outra regra.
- Aprender o cadastro com as correções do operador (story 4) reduziria os "sem sugestão".

## Relations

- part_of [[docuparser/decisions/roadmap-doc-type-identification-classification-merging-backlog-jira]]
- depends_on [[docuparser/decisions/plano-de-contas-por-condominio-escopo-e-modelo]]
