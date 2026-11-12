---
title: Casamento NF e boleto por CNPJ e valor
type: note
permalink: docuparser/decisions/casamento-nf-e-boleto-por-cnpj-e-valor
tags:
- doc-merging
- pagamento
- pipeline
---

## Decisão

Story 3 do Epic 3 do [[Roadmap — Doc Type Identification, Classification, Merging (backlog Jira)]]
implementada de ponta a ponta, sem esperar as stories 1 (rastreio de origem) e 2
(`PaymentProcess`), que ainda não existem no código.

- **Regra** (`documents/services/payment_matching.py`, `is_match`): CNPJ do fornecedor na
  nota (`cnpj_fornecedor`) igual ao do beneficiário no boleto (`cnpj_cpf_beneficiario`) e
  valor do boleto menor ou igual ao da nota (`valor_nota`; no boleto `valor_boleto`, com
  `valor_documento` de reserva). Boleto maior ou CNPJ diferente não casa.
- **Parcelamento**: cada boleto é avaliado sozinho contra a nota. A soma das parcelas não é
  limitada; quem confere é a confirmação humana. Uma nota casa com N boletos e um boleto
  com N notas.
- **Só CNPJ válido casa** (CPF, CNPJ inválido ou valor ausente/zero não geram candidato).
  Papel do documento (nota ou boleto) vem dos campos extraídos, não do `schema_id`, que varia.
- **Resultado é sugestão**: `documents.PaymentMatch` (migration `0018`), único por par
  nota+boleto, com CNPJ e valores usados. Nasce `SUGGESTED`; a confirmação obrigatória
  (story 4) ainda não existe. Rodar de novo não duplica nem mexe em linhas existentes.
- **Janela de tempo**: como o rastreio de origem não existe, o candidato é qualquer documento
  recebido a até `PAYMENT_MATCH_WINDOW_HOURS` (padrão 72, variável de ambiente) antes ou
  depois de `received_at`. O valor de 72h é suposição e deve ser revisto. Quando o
  `source_thread_id` existir, só muda a busca de candidatos em `run_payment_matching`.
- **Gatilho**: `run_payment_matching_safely` roda logo depois de `run_classification_safely`
  nos três pontos que gravam extração com campos (`auto_extract_after_ocr`,
  `run_langextract_for_document`, `consume_extraction_completed`). Nunca derruba o
  processamento. Usa a versão ativa dos campos, então valor editado pelo operador vale.
- Documentos `REJECTED` não são candidatos.

## Não feito

- Refazer o casamento quando o operador edita CNPJ ou valor na validação.
- API e tela para ver as sugestões; evento de auditoria (`DocumentEvent`).
- Exigir o mesmo condomínio no par (a regra do ticket é só CNPJ e valor).

## Testes

`documents/tests/test_payment_matching.py`: os quatro casos, parcelamento nos dois sentidos,
janela, idempotência, edição do operador e os três gatilhos do pipeline. Mutação verificada:
remover cada chamada do pipeline ou trocar `<=` por `<` quebra testes.

## Relations

- relates_to [[Identificação do condomínio e classificação ligada ao pipeline]]
