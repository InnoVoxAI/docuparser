# `unidades`

**Status:** ✅ Disponível · **Papel no projeto:** Apoio

## O que é

As unidades (apartamentos/salas) de cada condomínio, com os dados do proprietário. Relevante para documentos endereçados a uma unidade específica, não ao condomínio como um todo.

## Chamada

| | |
|---|---|
| **Path** | `GET /v2/condor/unidades` |
| **Métodos sondados** | `GET` apenas — o spike é read-only por construção (RI-001). Escrita não foi testada e está fora do escopo da Fase B |
| **Parâmetro obrigatório** | nenhum identificado |
| **HTTP observado** | `200` |
| **Registros na sonda** | 5 |
| **Campos descobertos** | 49 |

## Campos descobertos (49)

Nomes reais da API, em notação húngara. O prefixo indica o tipo.

**Campos sem prefixo (derivados/agregados)** (11)

```
celular_proprietario, condominio_formatado, cpf_proprietario, email_proprietario
forma_entrega_proprietario, nome_formatado, nome_proprietario, rg_proprietario
telefone_proprietario, tipo_proprietario, utiliza_app
```

**Datas** (1)

```
dt_nascimento_proprietario
```

**Flags / booleanos** (10)

```
fl_bloqueargeracaoremessa_uni, fl_condoworkssincro_uni, fl_descontounidade_uni, fl_escritorio_select
fl_notificadocorteagua_uni, fl_participainformerendimento_uni, fl_relogioinvertido_uni, fl_statusfin_uni
fl_statusgruvi_uni, fl_unidade_vazia_uni
```

**Identificadores e chaves estrangeiras** (6)

```
id_condominio_cond, id_condominio_cond1, id_escritorio_esc, id_grupo_ugbu
id_proprietario, id_unidade_uni
```

**Numéricos** (5)

```
nm_abatimento_uni, nm_fracao_real_uni, nm_fracao_uni, nm_txdesconto_uni
nm_vencimento_uni
```

**Texto (string)** (12)

```
st_bloco_uni, st_fantasia_cond, st_grupo_ugbu, st_identificacao_uni
st_label_cond, st_metragem_uni, st_msgerrogruvi_uni, st_nome_cond
st_sacado2_uni, st_sacado_uni, st_senha_site_uni, st_unidade_uni
```

**Texto longo** (3)

```
tx_etiquetainq_uni, tx_etiquetaprop_uni, tx_observacao_uni
```

**Valores monetários** (1)

```
vl_credito_uni
```

## Encaminhamento

- Sondado com sucesso. Campos e formato registrados.


---

_Gerado a partir de `fase-b-spike/achados/execucoes/2026-08-07/achados.json`. Ver [RELATORIO-ACHADOS.md](../fase-b-spike/achados/RELATORIO-ACHADOS.md)._
