# `fornecedores`

**Status:** ✅ Disponível · **Papel no projeto:** Contexto

## O que é

Os fornecedores/contatos da administradora. **Achado crítico da Fase A: o fornecedor é compartilhado entre condomínios**, enquanto a despesa é por condomínio — por isso o CNPJ do fornecedor nunca serve como chave de associação.

## Chamada

| | |
|---|---|
| **Path** | `GET /v2/condor/fornecedores` |
| **Métodos sondados** | `GET` apenas — o spike é read-only por construção (RI-001). Escrita não foi testada e está fora do escopo da Fase B |
| **Parâmetro obrigatório** | nenhum identificado |
| **HTTP observado** | `200` |
| **Registros na sonda** | 5 |
| **Campos descobertos** | 83 |

## Campos descobertos (83)

Nomes reais da API, em notação húngara. O prefixo indica o tipo.

**Datas** (5)

```
dt_alteracao_con, dt_alteracaoformapagamento_con, dt_nascimento_con, dt_reputacao_con
dt_trocacartao_con
```

**Campos sem prefixo (derivados/agregados)** (2)

```
favorecido_pix, nome_formatado
```

**Flags / booleanos** (13)

```
fl_boletounificado_con, fl_ignlancprovisaocontabil_con, fl_inativo_con, fl_itensopcionaisdebitoautomatico_con
fl_notificacao_con, fl_notificarsms_con, fl_pagamentopref_con, fl_politicadados_con
fl_recebedor_con, fl_sexo_con, fl_statuscartao_con, fl_statusgruvi_con
fl_tipoconta_con
```

**Identificadores e chaves estrangeiras** (10)

```
id_classificacaotributaria_ctri, id_classservicoprestado_csp, id_cnae_cnae, id_codigo_tfor
id_condominio_cond, id_contato_con, id_forma_frecb, id_forma_pag
id_naturezajuridica_njur, id_tipocontato_tcon
```

**Numéricos** (4)

```
nm_cartao_con, nm_qtdtrocacartao_con, nm_reputacao_con, nm_rpasequencial_con
```

**Texto (string)** (48)

```
st_agencia_con, st_anovalidade_con, st_bairro_con, st_banco_con
st_campoextragateway_con, st_cartaobandeira_con, st_cep_con, st_cgc_con
st_chave_con, st_chavegruvi_con, st_cidade_con, st_classificacao_servico_prestado
st_classificacao_tributaria, st_cnae, st_codigodocliente_con, st_complemento_con
st_contabancaria_con, st_contacontabil_con, st_cpf_con, st_cpfcnpjrecebedor_con
st_cpfpagamentoterceiro_con, st_documentoportador_con, st_email_con, st_endereco_con
st_estado_con, st_falarcom_con, st_fantasia_con, st_fax_con
st_identificadorexterno_con, st_inscricaomunicipal_con, st_inss_con, st_mesvalidade_con
st_msgerrogruvi_con, st_natureza_juridica, st_nome_con, st_nomecartao_con
st_nomepagamentoterceiro_con, st_nomeportador_con, st_nomerecebedor_con, st_numeroendereco_con
st_operacao_con, st_orgaoemissor_con, st_pis_con, st_rg_con
st_telefone_con, st_telefoneportador_con, st_tidcancelamento_con, st_tokentemporario_con
```

**Texto longo** (1)

```
tx_observacao_con
```

## Encaminhamento

- Sondado com sucesso. Campos e formato registrados.


---

_Gerado a partir de `fase-b-spike/achados/execucoes/2026-08-07/achados.json`. Ver [RELATORIO-ACHADOS.md](../fase-b-spike/achados/RELATORIO-ACHADOS.md)._
