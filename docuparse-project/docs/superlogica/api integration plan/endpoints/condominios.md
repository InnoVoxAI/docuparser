# `condominios`

**Status:** ✅ Disponível · **Papel no projeto:** ⭐ Núcleo da associação

## O que é

A entidade central de todo o projeto. Cada condomínio administrado pela administradora é um registro aqui, com CNPJ, endereço, dados fiscais e parâmetros de cobrança. **É contra este cadastro que a regra de associação documento↔condomínio é testada** — o CNPJ extraído do documento é procurado aqui.

## Chamada

| | |
|---|---|
| **Path** | `GET /v2/condor/condominios` |
| **Métodos sondados** | `GET` apenas — o spike é read-only por construção (RI-001). Escrita não foi testada e está fora do escopo da Fase B |
| **Parâmetro obrigatório** | `id` — sem ele responde `403 "Id do condomínio não informado"` |
| **HTTP observado** | `200` |
| **Registros na sonda** | 1 |
| **Campos descobertos** | 109 |

> `id=todos` devolve a carteira inteira; um id numérico devolve um condomínio.

## Campos descobertos (109)

Nomes reais da API, em notação húngara. O prefixo indica o tipo.

**Datas** (10)

```
dt_ativacao_usu, dt_criacao_cond, dt_desativacao_usu, dt_diadebito_cond
dt_diavencimento_cond, dt_expiracaoaccesstoken_usu, dt_inauguracao_cond, dt_ultimoacessodesktop_usu
dt_ultimoacessoweb_usu, dt_ultimologin_usu
```

**Campos sem prefixo (derivados/agregados)** (1)

```
escritorio_juridico
```

**Flags / booleanos** (22)

```
fl_ativo_cond, fl_bloqueiodesktop_usu, fl_centralizadorefdreinf_cond, fl_descontoapenascontas_cond
fl_descontovalorfixo2_cond, fl_descontovalorfixo3_cond, fl_descontovalorfixo_cond, fl_detector_cond
fl_elevadorbloco_cond, fl_extintores_cond, fl_garantido_cond, fl_hidrantes_cond
fl_manobrista_cond, fl_sincronizarmongo_usu, fl_sprinklers_cond, fl_status_implantacao
fl_statusgruvi_usu, fl_tipo_usu, fl_tipocondominio_cond, fl_tipoestrutura_cond
fl_usuariodesativado_usu, fl_versaoautenticacao_usu
```

**Identificadores e chaves estrangeiras** (14)

```
id_classificacaotributaria_ctri, id_cnae_cnae, id_condominio_cond, id_contato_vazia_con
id_escritorio_esc, id_licitamais_cond, id_naturezajuridica_njur, id_planoconta_plc
id_tipocobranca_tco, id_tipocondominio_tcon, id_tipojuros_cond, id_usuario_usu
id_usuariodesativacao_cond, id_usuarioqueautorizou_usu
```

**Numéricos** (18)

```
nm_descontoatedia2_cond, nm_descontoatedia3_cond, nm_descontoatedia_cond, nm_diasparaatualizar_cond
nm_funcionarios_cond, nm_iniciomes, nm_metrosquadrados_cond, nm_qtdloginsdesktop_usu
nm_qtdloginsweb_usu, nm_txdesconto2_cond, nm_txdesconto3_cond, nm_txdesconto_cond
nm_txfundocx_cond, nm_txhonorario_cond, nm_txhonorario_esc, nm_txjuros_cond
nm_txmulta_cond, nm_vagas_cond
```

**Texto (string)** (43)

```
st_accesstoken_usu, st_acesso_usu, st_acessosdesktop_usu, st_apelido_usu
st_apptoken_usu, st_authtype_usu, st_bairro_cond, st_cep_cond
st_chavegruvi_usu, st_cidade_cond, st_classificacao_tributaria, st_cnae
st_codigo_cnae, st_codigo_ctri, st_codigo_njur, st_complemento_cond
st_cpf_cond, st_descricao_cnae, st_descricao_ctri, st_descricao_njur
st_email_cond, st_endereco_cond, st_estado_cond, st_fantasia_cond
st_fax_cond, st_fracao_cond, st_inadimplente_cond, st_incrementar
st_inscrestadual_cond, st_inscrmunicipal_cond, st_ipsliberados_usu, st_label_cond
st_md5logo_usu, st_md5logogrande_usu, st_msgerrogruvi_usu, st_natureza_juridica
st_nome_cond, st_nome_usu, st_observacao_cond, st_senha_usu
st_telefone_cond, st_uf_uf, st_url_cond
```

**Valores monetários** (1)

```
vl_limitecredito_cond
```

## Encaminhamento

- Sondado com sucesso. Campos e formato registrados.


---

_Gerado a partir de `fase-b-spike/achados/execucoes/2026-08-07/achados.json`. Ver [RELATORIO-ACHADOS.md](../fase-b-spike/achados/RELATORIO-ACHADOS.md)._
