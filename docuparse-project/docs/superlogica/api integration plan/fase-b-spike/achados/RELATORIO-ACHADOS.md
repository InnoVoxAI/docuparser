# RELATÓRIO DE ACHADOS — spike de descoberta (Fase B)

**Status: Fases 0–3 EXECUTADAS. Fase 4 (regra de associação) NÃO EXECUTADA.**

_Execução: 2026-08-07 19:15 · `base_url` `https://api.superlogica.net/v2` · modo: **completo** ·
artefatos em `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/`._

---

## 0. Como ler este documento

### O que ele é

O **entregável da Fase B**. O spike é uma ferramenta descartável; o que sobrevive a ela é este
relatório. Cada seção abaixo pega uma pergunta técnica que a Fase A deixou **em aberto** e diz
o que a sondagem real da API respondeu.

### Como os resultados foram obtidos

| | |
|---|---|
| **Script executado** | [`discovery_spike.py`](../ferramenta/discovery_spike.py) |
| **Comando** | `./run_script.sh python3 "docuparse-project/docs/superlogica/api integration plan/fase-b-spike/ferramenta/discovery_spike.py" -v` |
| **Modo** | completo (todos os controllers candidatos), fases 0 a 3 |
| **Execução** | 2026-08-07 19:15 · `base_url` `https://api.superlogica.net/v2` |
| **Natureza** | 100% READ-ONLY — só `GET`, guarda rígida no cliente HTTP (RI-001) |
| **Artefatos crus** | `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/achados.json`, `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/achados.csv` (fora do git) |
| **Auto-verificação** | 28/28 checagens offline passando |

Todo dado deste relatório **sai desses artefatos**. Nada aqui vem de observação manual de
terminal — quando algo foi descoberto sondando à mão, virou comportamento da ferramenta antes
de virar linha deste documento.

### Onde ele se encaixa

```
FASE A (concluída)                FASE B (aqui)                    FASE C (não iniciada)
─────────────────                 ─────────────                    ────────────────────
estudo-api-...md                  discovery_spike.py               Specify da integração
  §7: 9 perguntas [HIP]  ────►      executa e mede       ────►       (a escrever)
pontos-a-esclarecer...md          RELATORIO-ACHADOS.md
  H1–H8 (humanas)                   ESTE documento
```

### Documentos relacionados

| Documento | Relação com este relatório |
|---|---|
| [`estudo-api-superlogica-condominios-docuparse.md`](../../fase-a-estudo/estudo-api-superlogica-condominios-docuparse.md) | **A origem.** O §7 lista as 9 perguntas que só a API responde. Este relatório as responde uma a uma |
| [`plano-fase-b-spike-descoberta.md`](../plano-fase-b-spike-descoberta.md) | O plano que definiu as Fases 0–5 do spike e o DoD |
| [`README-discovery-spike.md`](../ferramenta/README-discovery-spike.md) | Como rodar a ferramenta (modos, variáveis, formato da amostra) |
| [`pontos-a-esclarecer-validacao-humana.md`](../../fase-a-estudo/pontos-a-esclarecer-validacao-humana.md) | H1–H8, decisões **humanas**. Este relatório **não** as resolve |
| [`docs/specs/015-superlogica-discovery-spike/spec.md`](../../../../../../docs/specs/015-superlogica-discovery-spike/spec.md) | A spec formal do spike (requisitos, restrições, contratos de saída) |
| [`estado atual discovery superlogica.md`](../../00-visao-geral/estado%20atual%20discovery%20superlogica.md) | Recapitulação do processo: em que pé está cada fase e o que falta |
| [`restricoes-criticas.md`](../../00-visao-geral/restricoes-criticas.md) | As 14 restrições que condicionam a Fase C, derivadas destes achados |
| [`endpoints/`](../../endpoints/README.md) | Um documento por endpoint: o que é, campos, status |

### ⚠️ Sobre "reescrever os `[HIP]`"

O plano da Fase B previa que a saída do spike **reescreveria** as tags de confiança
(`[HIP] → [DOC]`) dentro do estudo da Fase A. **Isso não foi feito.**

O `estudo-api-...md` continua **intocado**, com suas **21 tags `[HIP]` originais**. O que existe
é **este documento novo**, que responde às mesmas perguntas do §7 — mas nenhum leitor do estudo
da Fase A saberá disso só lendo o estudo.

**Ação pendente, não executada:** decidir entre (a) atualizar as tags no estudo da Fase A
apontando para cá, ou (b) adicionar um aviso no topo dele remetendo a este relatório. Enquanto
nenhuma das duas acontecer, **o estudo da Fase A está desatualizado** em pelo menos 5 pontos —
`ST_CGC_CON` como campo de CNPJ (errado, é `st_cpf_cond`), o modelo de erro, o parâmetro
obrigatório `id`, quais controllers existem e o formato de data.

### ⚠️ Ressalva que atravessa o relatório inteiro — CONFIRMADA

A credencial dá acesso a **1 condomínio apenas** (`id_condominio_cond=7`, "COND. EDF. BETULA"),
verificado junto a quem a forneceu (2026-08-07). Não é artefato de medição: é o escopo real da
credencial *por enquanto*. Toda conclusão que dependa de **volume de carteira** está marcada
como não conclusiva, e a Fase 4 fica limitada à metade de cobertura (ver §5/§7 ⭐).

### Legenda de status

| | |
|---|---|
| ✅ **RESOLVIDO** | A sondagem respondeu; vale como fato |
| ⚠️ **PARCIAL** | Parte respondida, parte ainda aberta |
| ⛔ **NÃO CONCLUSIVO** | Rodou, mas o ambiente não sustenta a conclusão |
| ⬜ **NÃO EXECUTADO** | Não rodou; nada foi inventado no lugar |

---

## 1. Achados por item do §7 da Fase A

### §7.4 — Autenticação e modelo de erro ✅ **RESOLVIDO**

Chamada válida: **HTTP 200**, `autenticou: true`. A credencial funciona.

**A API está atrás de um gateway Sensedia**, e há **duas camadas** que reportam erro de
formas diferentes:

| Camada | Situação | Status | Corpo |
|---|---|---|---|
| Gateway (Sensedia) | credencial inválida/ausente | `401` | texto puro (`Check docs.sensedia.com`) — **não é JSON** |
| Backend (Superlógica) | parâmetro obrigatório faltando | `403` | JSON `{"status":"403","msg":"…"}` |
| Backend (Superlógica) | path inexistente | `404` | JSON com `msg` |
| Backend (Superlógica) | erro interno | `500` | JSON com `msg` |

**O modelo de erro é híbrido:** o status HTTP diz *que* falhou, o corpo diz *por quê*, e a
informação acionável está no corpo. Um cliente que só olhasse o status trataria o `403` de
parâmetro faltando como falha de permissão, e o `500` como transitório — entrando em retry
eterno contra erros que retry nenhum resolve.

**Para a Fase C:** a camada de auth/retry precisa ler `msg` e separar *falha transitória* de
*recusa* e de *erro de chamada*. Nenhum dos dois últimos é retryable.

- Tokens vão no header a cada requisição → **stateless**.
- **Expiração continua não verificável** numa execução única. Em aberto.
- O padrão v1 (`status` no corpo, ≥100 = erro) **coexiste** com `msg` na v2 — o `403` traz
  os dois.

#### Mapeamento das credenciais (confirmado por sondagem)

| Header | Recebe |
|---|---|
| `app_token` | **App token** |
| `access_token` | **Access token** |

O **Secret** não entra em nenhum dos dois — é rejeitado nas duas posições (401 do gateway).
Serve a outro fluxo. O spike não o consome.

---

### §7.1 / §7.8 — Endpoints e campos ✅ **RESOLVIDO**

**Descoberta que destrava tudo:** `condor/condominios` **exige o parâmetro `id`**. Sem ele,
responde `403 "Id do condomínio não informado"`. O coringa **`id=todos`** devolve a carteira.
Ids numéricos devolvem um condomínio específico. Os demais controllers **não** exigem `id`.

| controller | existe | HTTP | registros | campos | erro no corpo |
|---|---|---|---|---|---|
| `condominios` | ✅ | 200 | 1 | 109 | |
| `unidades` | ✅ | 200 | 5 | 49 | |
| `fornecedores` | ✅ | 200 | 5 | 83 | |
| `despesas` | ✅ | 200 | 2 | 97 | |
| `condominos` | ❌ | 404 | 0 | 0 | Não encontrado |
| `contatosunidade` | ❌ | 404 | 0 | 0 | Não encontrado |
| `cobrancas` | ❌ | 404 | 0 | 0 | Não encontrado |
| `planodecontas` | ❌ | 404 | 0 | 0 | Não encontrado |
| `notafiscal` | ⚠️ | 500 | 0 | 0 | `SQLSTATE[42S02]: Base table or view not found` |

**4 dos 9 controllers candidatos existem.** Os quatro `404` precisam de descoberta manual via
inspeção do tráfego do ERP — o nome do controller provavelmente difere do chutado na Fase A.

`notafiscal` merece nota à parte: o `500` traz um **erro de SQL vazando para o cliente**
(`Base table or view not found`). Não é "não existe" — é um endpoint quebrado do lado do ERP,
ou não provisionado para esta licença. Vale reportar ao Superlógica.

#### Envelope das respostas

As entidades vêm **duplamente aninhadas**: `[ { "condominio": [ {…109 campos…} ] } ]`. Sem
desembrulhar, o achado reportaria 1 registro com um único "campo" chamado `condominio`.

#### Nomes de campo descobertos (§7.2-campo)

Os dois campos centrais são **pontas opostas da mesma operação** — a confusão entre eles é o
erro que mais custa caro, então vale a distinção explícita:

| | Campo | Papel | De onde vem o valor |
|---|---|---|---|
| 🔑 **Chave de busca** | **`st_cpf_cond`** | Onde o cadastro guarda o **CNPJ** do condomínio. É por ele que se **procura** | De fora: é o CNPJ que o DocuParse extraiu do documento |
| 🎯 **Resposta** | **`id_condominio_cond`** | **Identificador** do condomínio dentro do ERP (aqui: `7`). É o que se **obtém** do match | Do próprio ERP |
| | `st_nome_cond` | Nome legível (`COND. EDF. BETULA`) — para conferência humana | Do próprio ERP |

Em uma linha, é o que a Fase 4 faz:

```
índice:  { st_cpf_cond normalizado   →   id_condominio_cond }
              ↑ o que se procura            ↑ o que se obtém
          (vem do documento)          (é comparado com o gabarito)
```

Duas consequências práticas:

- **O `condominio_esperado_id` da amostra rotulada é um `id_condominio_cond`**, nunca um CNPJ.
- **É o `id_condominio_cond` que a integração usa depois** — lançar despesa no condomínio 7,
  listar unidades do condomínio 7. O CNPJ não serve para operar a API; serve só para achar o id.

Daí a regra de ouro do gabarito: ele **não pode** ser montado casando CNPJ, senão a resposta
seria produzida pela mesma chave que está sob teste.

`st_cpf_cond` tem nome enganoso — chama-se "cpf" mas guarda 14 dígitos (CNPJ). O `[HIP]` da
Fase A chutava `ST_CGC_CON` → **descartado**. Ambos os nomes vieram de heurística; a conferência
por inspeção do tráfego do ERP continua recomendada, e `SL_FIELD_CNPJ` / `SL_FIELD_ID` permitem
fixá-los.

⚠️ **O cadastro de condomínio expõe campos de credencial** — `st_apptoken_usu`,
`st_accesstoken_usu`, `st_senha_usu`, `st_chavegruvi_usu`. Vazios neste condomínio, mas a
ferramenta agora os redige por nome antes de gravar qualquer amostra.

---

### §7.2-filtro / §7.5 / §7.6 / §7.7 — Mecânica ⚠️ **PARCIAL**

#### Filtro server-side por CNPJ — ⛔ **NÃO CONCLUSIVO**

Os 6 parâmetros candidatos (`CNPJ`, `cnpj`, `pesquisa`, `busca`, `ST_CGC_CON`, `ST_CNPJ_CON`)
foram testados com um CNPJ real da carteira. Nenhum estreitou o resultado — **mas com 1
condomínio visível, estreitar é impossível por construção**: com ou sem filtro, o resultado é
o mesmo registro.

**A bifurcação de arquitetura mais cara da Fase C segue indecidida:**

> Se não existir filtro server-side por CNPJ, **a sincronização local da carteira passa a ser
> obrigatória** e frescor/webhook deixa de ser opcional.

Para decidir, repetir contra uma carteira com **2 ou mais** condomínios. (Uma versão anterior
deste relatório concluía "SEM filtro" — era falsa confiança, corrigida na ferramenta.)

#### Paginação — ⚠️ não conclusivo

`itensPorPagina`, `limit` e `porPagina` foram aceitos, mas com baseline de 1 registro
"respeitou o limite" é trivialmente verdadeiro e **não prova** que a paginação funciona.
Também depende de carteira maior.

#### Formato de data — ✅ observado

Só o formato **com barra** aparece nas respostas (ex.: `08/10/2020`); zero ocorrências de ISO.
**A leitura não distingue `DD/MM` de `MM/DD`** — o teste ativo depende de existir filtro de
data. Continua em aberto, e é o bug clássico da integração.

#### Rate limit — ✅ sem sinal de limite

Burst de 8 requisições: **8 × HTTP 200**, nenhum `429`, **nenhum cabeçalho de rate limit**
exposto. O limite real não é público. **Throttle conservador na integração.**

#### Lote — ⬜ deferido

O padrão `params[]` da v1 era `POST`. Confirmação depende do caminho de escrita, fora do
escopo read-only.

---

### §7.3 — Anexos na leitura ✅ **RESOLVIDO** (leitura) · ⬜ download e escrita em aberto

2 despesas amostradas. Campos candidatos a anexo:

| Campo | Conteúdo |
|---|---|
| **`arquivos`** | **Lista de objetos com metadado de anexo** — o campo real |
| `documentos_pendentes` | Lista vazia (`[]`) na amostra |
| `st_documento_des`, `st_serienota_des` | Vazios — não são anexo, são número/série do documento |

#### O formato: nem URL, nem base64 — **referência por id + hash**

Esta era a bifurcação em aberto do §7.3, e está **decidida**. O anexo **não vem embutido** na
resposta da despesa: vem uma lista de metadados apontando para o arquivo.

Estrutura real observada (despesa `335373`, condomínio `7`):

```json
"arquivos": [
  {
    "id_arquivo_arq":  "125918",
    "st_nome_arq":     "Recibo de Pagamento (24)",
    "st_extensao_arq": "pdf",
    "st_hash_arq":     "e9cc9a43245cdbe3ec2fd9089bc24ea56ae8058e",
    "nm_tamanho_arq":  "7284",
    "dt_envio_arq":    "08/05/2026",
    "fl_vinculado_arq": "1",
    "id_despesa_des":  "335373",
    "id_parcela_pdes": "350457",
    "etiquetas": [ { "st_nomeabreviadoetiqueta_eti": "Doc. Pgto" } ]
  }
]
```

Em português: *a despesa 335373 tem um anexo — PDF de 7,3 KB chamado "Recibo de Pagamento (24)",
id 125918, etiquetado como "Doc. Pgto"*.

**Campos que importam para a Fase 4:**

| Campo | Para quê |
|---|---|
| `id_arquivo_arq` | Chave para baixar o arquivo |
| `st_hash_arq` | SHA-1 do conteúdo — serve para deduplicar e verificar integridade |
| `st_extensao_arq` | Filtrar só `pdf` ao montar a amostra |
| `nm_tamanho_arq` | Bytes — descartar arquivos vazios/corrompidos antes de gastar OCR |
| `etiquetas[].st_nomeabreviadoetiqueta_eti` | Classificação humana do anexo (`Doc. Pgto`, …) — **pista para o H7** |

> As **etiquetas** são um achado lateral relevante: o ERP já classifica o anexo por tipo, feito
> por pessoa. Pode servir de segunda fonte para o H7 (taxonomia de tipos de documento) e para
> segmentar as métricas da Fase 4 por tipo.

#### O que continua em aberto

1. **O endpoint de download.** Sabemos o identificador, não o path que troca `id_arquivo_arq`
   pelos bytes. **Resolvível só com `GET`** — não depende de decisão humana.
2. **A escrita.** Confirmar se a despesa *aceita* anexo, e em que formato, só se resolve
   escrevendo → passo autorizado à parte, fora do spike (H1).

**Consequência para a Fase 4:** o caminho de montagem da amostra está desenhado —
`despesa → id_condominio_cond` (gabarito) e `despesa → arquivos[].id_arquivo_arq` → baixar PDF →
DocuParse → `cnpj_papel_condominio`. Falta só o passo de download.

> ⚠️ Repare em `dt_envio_arq: "08/05/2026"` e `dt_vencimento_pdes: "08/05/2026 00:00:00"`. É o
> [R-04](../../00-visao-geral/restricoes-criticas.md#r-04) num campo real: **8 de maio** ou
> **5 de agosto**? Ambos plausíveis. A ambiguidade não é teórica.

---

### ⭐ §5 / §7 ⭐ — Regra de associação ⬜ **NÃO EXECUTADA**

Não rodou por **falta de amostra rotulada**. O bloqueio técnico caiu — `st_cpf_cond` e
`id_condominio_cond` estão identificados, então a Fase 4 tem como montar o índice.

**Nenhum go/no-go foi emitido.** A regra documento↔condomínio permanece **hipótese não testada**.

#### A Fase 4 se parte em duas metades, e só uma é acessível nesta credencial

Com **1 condomínio** (confirmado), o índice tem uma entrada só. Isso não zera a fase — separa o
que ela mede:

| Métrica | Acessível aqui | Por quê |
|---|---|---|
| % sem CNPJ | ✅ | Mede se o DocuParse extraiu algum CNPJ do documento |
| % CNPJ inválido | ✅ | DV local; pega erro de OCR |
| Cobertura (% que casou) | ✅ | O CNPJ extraído bate com o do cadastro |
| **Precisão / % ERRADO** | ❌ | **Não há outro condomínio com que confundir** |

Ou seja: dá para rodar a Fase 4 aqui como **ensaio** — valida o encanamento de ponta a ponta e
mede a **qualidade de extração do DocuParse**, que é informação real. O que **não** sai é o
go/no-go, porque ele se apoia no `% ERRADO` — o número de risco financeiro/jurídico e o motivo
de a fase existir. Confundir um condomínio com outro exige que haja outro.

**O go/no-go exige um ambiente com a carteira real (2+ condomínios).**

#### Onde obter o gabarito: `condor/despesas`

O registro de despesa (97 campos) traz, no mesmo lugar, o documento e a resposta certa:

| Campo | Papel na amostra |
|---|---|
| `id_condominio_cond` | **É o `condominio_esperado_id`** — atribuído por uma pessoa ao lançar a despesa |
| `st_fantasia_cond` | Nome do condomínio, para conferência humana |
| `arquivos` | O anexo — o documento a ser processado pelo DocuParse |

O gabarito é **independente da chave sob teste**: quem lançou a despesa escolheu o condomínio
por julgamento humano, não casando CNPJ. É a condição que valida a medição.

⚠️ **Duas armadilhas de montagem:**

1. O `id_condominio_cond` aparece em dois papéis opostos — vindo do **índice de CNPJ** é o
   *palpite*; vindo do **registro da despesa** é a *verdade*. Usar o mesmo valor nos dois lados
   compara algo consigo mesmo e dá 100% sempre.
2. **O `cnpj_papel_condominio` tem que sair do PDF, via DocuParse.** Tirá-lo dos campos
   estruturados da despesa testaria o ERP contra o ERP — não a extração, que é o que está sob
   julgamento. Da API pode vir tudo, menos esse campo.

**Pré-requisito ainda aberto:** o formato do campo `arquivos` (URL / base64 / id) não foi
classificado — sem isso não há como puxar os PDFs programaticamente. Ver §7.3.

---

## 2. Correções feitas na ferramenta durante esta execução

A execução expôs sete defeitos, todos corrigidos e cobertos por auto-verificação
(**13 → 28 checagens** offline):

| # | Defeito | Impacto se não corrigido |
|---|---|---|
| 1 | `autenticou` era `status != 401` | Reportava autenticação OK sob erro de permissão |
| 2 | Erro no corpo só era buscado em `status` (v1) | O `msg` da v2 passava despercebido |
| 3 | Envelope de erro contava como registro | `msg` viraria "campo" da entidade |
| 4 | `probe()` não mandava parâmetro obrigatório | **Todos os controllers dariam falso "não existe"** |
| 5 | `extract_records` não desembrulhava o aninhamento | Nenhum campo seria descoberto, com dados válidos na mão |
| 6 | `mask_pii_in_record` só mascarava CPF/CNPJ | **Gravaria tokens e senhas em disco** (RI-002/RI-004) |
| 7 | `guess_id_field` escolhia por contagem | Elegeu `id_planoconta_plc`; o índice da Fase 4 mapearia CNPJ → id errado, **corrompendo o go/no-go em silêncio** |

Mais três ajustes de honestidade: a conclusão do filtro e a da paginação agora se declaram
**não conclusivas** quando a carteira é pequena demais para sustentá-las; a sonda de rate limit
passou a mandar o parâmetro obrigatório (antes media 8 × 403, não 8 × 200); e a Fase 4 agora
**retém o go/no-go** e anula `precisao_%` / `errado_%` quando o índice tem menos de 2
condomínios — em vez de imprimir um `errado_% = 0` que seria artefato do ambiente.

Fora da ferramenta: [`run_script.sh`](../../../../../../run_script.sh) tinha o caminho `/docuparser`
do dev container hardcoded e não carregava o `.env` num clone no host.

---

## 3. Encaminhamento

**Bloqueadores da Fase 4, em ordem:**

1. **Formato do campo `arquivos`** (URL / base64 / id). Deixou de ser curiosidade do §7.3 e virou
   pré-requisito da amostra: é por ele que se puxa o PDF de cada despesa. Resolvível por
   inspeção do tráfego do ERP, sem depender de credencial nova.
2. **H7** — mapa tipo de documento → qual campo é o papel-condomínio. Define o que entra em
   `cnpj_papel_condominio` por tipo.
3. **Ambiente com a carteira real** (2+ condomínios). Destrava o **go/no-go**, a bifurcação do
   filtro e a paginação — as três conclusões que esta credencial não sustenta. É o item de maior
   alcance, e o único que não tem contorno técnico.

Com 1 e 2 resolvidos, o **ensaio de cobertura** já pode rodar nesta credencial e entregar a
qualidade de extração do DocuParse, sem esperar o item 3.

**O SELECT não serve como fonte de gabarito.** O `mapa_download.csv` é organizado por *categoria
do plano de contas* (`pasta_destino`, `categoria_bruta`, `fornecedor`) e **não tem dimensão de
condomínio** — o pipeline pressupõe um condomínio só. Ele fornece documentos, não a associação
correta.

**Descoberta manual pendente (não depende de credencial):** os 4 controllers `404`
(`condominos`, `contatosunidade`, `cobrancas`, `planodecontas`) e o formato do campo `arquivos`
das despesas, ambos resolvíveis por inspeção do tráfego do ERP.

**Nada foi escrito no ERP.** Todas as requisições foram `GET`, garantido pela guarda do cliente
HTTP (RI-001).
