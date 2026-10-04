---
title: docs_por_plano_de_contas - dataset de documentos reais
type: note
permalink: docuparser/reference/docs-por-plano-de-contas-dataset-de-documentos-reais
tags:
- plano-de-contas
- dataset
- boleto
---

`docs_por_plano_de_contas/` (raiz do repo, fora do git via `.git/info/exclude`, não
`.gitignore`, por decisão do usuário: contém dados pessoais) tem documentos
reais que a cliente recebe, organizados por conta do plano de contas: cada pasta é uma
conta (38 pastas, ex. Água, Energia, Gás, Inss, Dedetização, Manutenções) e cada
documento vem como `.pdf` mais o texto extraído em `.txt` (95 documentos).

Serve de gabarito para o motor de regras de classificação: pasta = conta esperada.

Fatos levantados em 2026-10-04:

- Dois condomínios pagadores: Avis Liberta (02.819.556/0001-30) e Plátano
  (41.090.325/0001-90). A administradora (tenant) é Jeane Gomes Gestão Imobiliária
  (35.318.863/0001-96), que cobra a taxa de "Administração".
- Para o usuário, DARF e RPA chegam como boleto (documento de cobrança/pagamento).
- O CNPJ do fornecedor separa sozinho a maioria das contas: 51 de 95 documentos têm um
  fornecedor que só aparece numa conta; 8 só têm fornecedor que aparece em duas contas
  (Secovi, sindicato 08.078.021/0001-31, MS Instalações); 36 não têm CNPJ de fornecedor
  (DARF e GFD do próprio condomínio, recibos de pessoa física, folha, OCR ruim).
- Intermediários de pagamento (Cora 37.880.206/0001-63, Safe2Pay 31.037.942/0001-78)
  aparecem como CNPJ no boleto e não identificam o fornecedor.
- A conta "Água" inclui serviços e insumos ligados à água (válvula redutora, saneantes),
  não só a fatura da concessionária (Compesa).
- Nas NFS-e, a chave de acesso embute o CNPJ do emissor.

## Relations

- relates_to [[docuparser/decisions/plano-de-contas-por-condominio-escopo-e-modelo]]
