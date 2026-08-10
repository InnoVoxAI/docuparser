# `despesas`

**Status:** ✅ Disponível · **Papel no projeto:** ⭐ Fonte do gabarito

## O que é

Os lançamentos de despesa. Cada despesa pertence a **um** condomínio (`id_condominio_cond`) e pode ter anexos (`arquivos`). **É a fonte do gabarito da Fase 4**: traz, pareados, o documento e o condomínio correto atribuído por uma pessoa.

## O campo `arquivos` — os anexos da despesa

O anexo **não vem embutido** na resposta. `arquivos` é uma **lista de metadados** apontando para
o arquivo: nem URL, nem base64 — **referência por id e hash**.

Exemplo real (despesa `335373`, condomínio `7` — COND. EDF. BETULA):

```json
"arquivos": [
  {
    "id_arquivo_arq":   "125918",
    "st_nome_arq":      "Recibo de Pagamento (24)",
    "st_extensao_arq":  "pdf",
    "st_hash_arq":      "e9cc9a43245cdbe3ec2fd9089bc24ea56ae8058e",
    "nm_tamanho_arq":   "7284",
    "dt_envio_arq":     "08/05/2026",
    "fl_vinculado_arq": "1",
    "id_despesa_des":   "335373",
    "id_parcela_pdes":  "350457",
    "etiquetas": [ { "st_nomeabreviadoetiqueta_eti": "Doc. Pgto" } ]
  }
]
```

| Campo | Para quê |
|---|---|
| `id_arquivo_arq` | Chave para baixar o arquivo |
| `st_hash_arq` | SHA-1 do conteúdo — deduplicação e verificação de integridade |
| `st_extensao_arq` | Filtrar só `pdf` ao montar a amostra |
| `nm_tamanho_arq` | Bytes — descartar arquivos vazios antes de gastar OCR |
| `etiquetas[]` | Classificação humana do anexo (`Doc. Pgto`, …) — pista para o **H7** |

O campo irmão `documentos_pendentes` veio como lista vazia (`[]`) na amostra.

> ⬜ **Em aberto:** o endpoint que troca `id_arquivo_arq` pelos bytes do PDF. 
> `GET`, sem depender de decisão humana.

## Por que este endpoint é a fonte do gabarito

```
despesa 335373
  ├── id_condominio_cond = 7 ──────────► condominio_esperado_id   (gabarito, humano)
  └── arquivos[0].id_arquivo_arq = 125918 ──► PDF ──DocuParse──► cnpj_papel_condominio
```

O gabarito é **independente da chave sob teste**: quem lançou a despesa escolheu o condomínio
por julgamento, não casando CNPJ. Ver
[R-06](../00-visao-geral/restricoes-criticas.md#r-06).

## Chamada

| | |
|---|---|
| **Path** | `GET /v2/condor/despesas` |
| **Métodos sondados** | `GET` apenas — o spike é read-only por construção (RI-001). Escrita não foi testada e está fora do escopo da Fase B |
| **Parâmetro obrigatório** | nenhum identificado |
| **HTTP observado** | `200` |
| **Registros na sonda** | 2 |
| **Campos descobertos** | 97 |

## Campos descobertos (97)

Nomes reais da API, em notação húngara. O prefixo indica o tipo.

**Campos sem prefixo (derivados/agregados)** (7)

```
apropriacao, arquivos, autenticar, contato
documentos_pendentes, fornecedor_formatado, resumo_lancamentos_fornecedor
```

**Datas** (6)

```
dt_despesa_des, dt_geracao_des, dt_liquidacao_pdes, dt_previsaocredito_pdes
dt_tributoperiodo_pdes, dt_vencimento_pdes
```

**Flags / booleanos** (9)

```
fl_liquidado_pdes, fl_mensal_des, fl_modelotrabalho_des, fl_pixtipochave_pdes
fl_recorrente_des, fl_remessastatus_pdes, fl_tipoconta_con, fl_tipocontribuinte_pdes
fl_tipotributo_pdes
```

**Identificadores e chaves estrangeiras** (21)

```
id_agenciabanco_agb, id_banco_banc, id_bordero_bor, id_cheque_pdes
id_condominio_cond, id_contabanco_cb, id_contato_con, id_despesa_des
id_favorecido_con, id_favorecido_fav, id_forma_pag, id_natrend_des
id_origemretencao_des, id_parcela_pdes, id_pj_pdes, id_planoconta_plc
id_portador_por, id_rv2_imposto_des, id_rv2_origem_des, id_tipo_doc
id_tipocontabanco_tcb
```

**Numéricos** (2)

```
nm_tagcriacao_pdes, nm_tagliquidacao_pdes
```

**Texto (string)** (40)

```
st_agencia_con, st_bairro_con, st_banco_con, st_cep_con
st_cidade_con, st_classificacao_servico_prestado, st_classificacao_tributaria, st_codautenticacaopag_pdes
st_codigobarras_pdes, st_codigoreceita_pdes, st_complemento_pdes, st_conta_cb
st_contabancaria_con, st_cpf_con, st_cpfcnpjrecebedor_con, st_descricao_cb
st_documento_des, st_endereco_con, st_envelopeetiqueta_pdes, st_estado_con
st_fantasia_con, st_fantasia_cond, st_identcontribuinte_pdes, st_msgretorno_pdes
st_natureza_rendimento, st_nome_banc, st_nome_con, st_nomecontribuinte_pdes
st_nomerecebedor_con, st_nomerecebedor_fav, st_numero_agb, st_observacao_des
st_observacaointerna_des, st_operacao_con, st_pis_con, st_pixchave_pdes
st_pixqrcode_pdes, st_porcentoreceitabruta_pdes, st_serienota_des, st_tributonumeroref_pdes
```

**Valores monetários** (12)

```
vl_desconto_pdes, vl_juros_pdes, vl_multa_pdes, vl_outrasentidades_pdes
vl_rv2_totalnf_des, vl_totalespeciais_pdes, vl_tributo_pdes, vl_tributoencargos_pdes
vl_tributomulta_pdes, vl_tributoreceitabruta_pdes, vl_valor_pdes, vl_valorbruto_pdes
```

## Encaminhamento

- Sondado com sucesso. Campos e formato registrados.


---

_Gerado a partir de `fase-b-spike/achados/execucoes/2026-08-07/achados.json`. Ver [RELATORIO-ACHADOS.md](../fase-b-spike/achados/RELATORIO-ACHADOS.md)._
