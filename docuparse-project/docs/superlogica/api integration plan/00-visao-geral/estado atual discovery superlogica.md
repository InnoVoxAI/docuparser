# Estado atual — Discovery Superlógica

_Atualizado em 2026-08-07 · projeto DocuParse × API Condomínios (Superlógica)_

> **Para que serve este documento:** responder "em que pé estamos e o que falta" sem precisar
> reconstruir o contexto lendo cinco arquivos. Se você voltou ao projeto depois de um tempo,
> comece por aqui.
>
> Os **achados técnicos** em si estão no [`RELATORIO-ACHADOS.md`](../fase-b-spike/achados/RELATORIO-ACHADOS.md). Este
> documento é sobre o **processo**: o que já rodou, o que sobrou, e como ler o que saiu.
>
> As **restrições que condicionam a Fase C** estão em
> [`restricoes-criticas.md`](restricoes-criticas.md) — leitura obrigatória antes de escrever
> código da integração.

---

## 1. O problema, em um parágrafo

O DocuParse extrai dados de documentos (nota fiscal, boleto, conta de consumo). O Superlógica é
o ERP onde esses documentos precisam ser arquivados, e ele organiza tudo **por condomínio**. A
ponte entre os dois mundos é uma hipótese: *"o CNPJ que o DocuParse extraiu do documento casa
com o CNPJ do cadastro do condomínio no Superlógica, e isso identifica o condomínio certo."*
Errar aí associa uma despesa ao condomínio errado num sistema financeiro — impacto financeiro e
jurídico real. **Todo o trabalho da Fase B existe para testar essa hipótese antes de construir
em cima dela.**

---

## 2. As três fases

| Fase | O que é | Status |
|---|---|---|
| **A** | Entendimento + estudo exploratório da API | ✅ **Concluída** |
| **B** | Spike de descoberta descartável — mede e reporta | 🟡 **Em andamento** (~70%) |
| **C** | Specify real da integração | ⬜ **Não iniciada** |

A Fase B se divide em 6 sub-fases, definidas no [plano](../fase-b-spike/plano-fase-b-spike-descoberta.md):

| Sub-fase | O que faz | Status |
|---|---|---|
| **0** | Autenticação e modelo de erro | ✅ Executada, resolvida |
| **1** | Endpoints e campos | ✅ Executada, resolvida |
| **2** | Filtro, paginação, data, rate limit, lote | ⚠️ Executada, **parcialmente conclusiva** |
| **3** | Anexos na leitura | ⚠️ Executada, formato não classificado |
| **4** ⭐ | **Validação da regra de associação** | ⬜ **Não executada** |
| **5** | Consolidação (o relatório) | ✅ Executada |

---

## 3. O que existe hoje, arquivo por arquivo

### Documentos

| Arquivo | Fase | O que é |
|---|---|---|
| [`estudo-api-superlogica-condominios-docuparse.md`](../fase-a-estudo/estudo-api-superlogica-condominios-docuparse.md) | A | Estudo da API. O **§7** lista as 9 perguntas que só a API responde |
| [`pontos-a-esclarecer-validacao-humana.md`](../fase-a-estudo/pontos-a-esclarecer-validacao-humana.md) | A | **H1–H8**: decisões de produto/negócio que exigem humano |
| [`roadmap-visual-docuparse-superlogica.md`](roadmap-visual-docuparse-superlogica.md) | A | Diagrama A→B→C (⚠️ desatualizado — ver §7) |
| [`plano-fase-b-spike-descoberta.md`](../fase-b-spike/plano-fase-b-spike-descoberta.md) | B | Plano do spike: sub-fases 0–5, tarefas, DoD |
| [`README-discovery-spike.md`](../fase-b-spike/ferramenta/README-discovery-spike.md) | B | Como rodar a ferramenta |
| [`RELATORIO-ACHADOS.md`](../fase-b-spike/achados/RELATORIO-ACHADOS.md) | B | **O entregável.** Os achados por item do §7 |
| **este arquivo** | B | Estado do processo |

### Código

| Arquivo | O que é |
|---|---|
| [`discovery_spike.py`](../fase-b-spike/ferramenta/discovery_spike.py) | A ferramenta. ~900 linhas, descartável, 100% read-only |
| [`amostra.exemplo.json`](../fase-b-spike/ferramenta/amostra.exemplo.json) | **Molde** do formato da amostra — dados fictícios, não roda |
| `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/` | Saídas da última execução (fora do git) |

### Spec Kit (SDD)

A spec 015 parou logo após o `/speckit-specify`:

| Artefato | Existe? |
|---|---|
| `spec.md` | ✅ (atualizada conforme os achados) |
| `checklists/requirements.md` | ✅ |
| `plan.md`, `research.md`, `tasks.md` | ❌ **nunca gerados** |

> **Nota de processo:** a spec foi escrita *retroativamente*, a partir de um script que já
> existia e funcionava. Rodar `/speckit-plan` + `/speckit-tasks` produziria plano e tarefas para
> algo já construído. A decisão pendente é tratar a 015 como **spec-de-registro** (documenta o
> contrato observável do spike) ou completar o ciclo formalmente.
>
> ⚠️ `.specify/feature.json` aponta hoje para `docs/specs/020-opentelemetry-tracing`. Qualquer
> comando spec-kit agora age sobre a 020, não sobre a 015.

---

## 4. Achados críticos até aqui

Os cinco que mais mudam o que vem depois. Detalhes completos no
[`RELATORIO-ACHADOS.md`](../fase-b-spike/achados/RELATORIO-ACHADOS.md).

### 4.1 A credencial enxerga 1 condomínio — e isso limita a Fase 4

Confirmado junto a quem forneceu os tokens: acesso a **1 condomínio**
(`id_condominio_cond=7`, "COND. EDF. BETULA"), *por enquanto*.

Consequência: a Fase 4 se parte em duas metades e só uma é acessível.

| Métrica | Mensurável aqui? |
|---|---|
| % sem CNPJ · % CNPJ inválido · cobertura | ✅ Sim — medem a **qualidade de extração do DocuParse** |
| **Precisão · % de associações ERRADAS** | ❌ **Não** — sem outro condomínio, não há com o que confundir |

O `% ERRADO` é o número de risco financeiro/jurídico, e é o que sustenta o go/no-go. **A
ferramenta agora retém o go/no-go explicitamente** quando o índice tem menos de 2 condomínios
(FR-057), em vez de imprimir um zero que seria artefato do ambiente.

### 4.2 `condor/condominios` exige o parâmetro `id`

Sem ele: `403 "Id do condomínio não informado"`. O coringa **`id=todos`** devolve a carteira.
Isso era invisível: o endpoint parecia quebrado. Os demais controllers não exigem `id`.

### 4.3 Os nomes de campo do §7.2 — um deles estava errado no estudo

| Papel | Campo real | O estudo dizia |
|---|---|---|
| CNPJ do condomínio (**chave de busca**) | **`st_cpf_cond`** | `ST_CGC_CON` ❌ |
| Id do condomínio (**resposta**) | **`id_condominio_cond`** | — |

`st_cpf_cond` tem nome enganoso: chama-se "cpf" e guarda 14 dígitos.

### 4.4 O modelo de erro é híbrido, em duas camadas

Gateway **Sensedia** na frente responde `401` em texto puro; o backend Superlógica responde
`403`/`404`/`500` com JSON `msg`. **O status HTTP diz que falhou, o corpo diz por quê.** Um
`500` aqui **não** é sinal de retry. Isso desenha a camada de auth/retry da Fase C.

### 4.5 O gabarito da amostra sai de `condor/despesas`

O registro de despesa traz `id_condominio_cond` (= o gabarito, atribuído por uma pessoa ao
lançar) e `arquivos` (o documento). Documento e resposta certa, pareados, no mesmo lugar — e o
gabarito é independente da chave sob teste.


---

## 5. O que falta

### 5.1 Caminho crítico da Fase 4

| # | Item | Depende de | Destrava |
|---|---|---|---|
| 1 | **Formato do campo `arquivos`** (URL / base64 / id) | Inspeção do tráfego do ERP — **não precisa de credencial nova** | Puxar os PDFs para montar a amostra |
| 2 | **H7** — mapa tipo de documento → campo papel-condomínio | Equipe DocuParse | O que entra em `cnpj_papel_condominio` |
| 3 | **Amostra rotulada** | Itens 1 e 2 | O ensaio de cobertura |
| 4 | **Carteira real (2+ condomínios)** | Terceiros | **Go/no-go**, bifurcação do filtro, paginação |

> Com **1 e 2** resolvidos, o **ensaio de cobertura já roda nesta credencial** e entrega a
> qualidade de extração do DocuParse — sem esperar o item 4.

### 5.2 Perguntas do §7 ainda abertas

| Item | Estado |
|---|---|
| §7.1 — paths de 4 controllers (`condominos`, `contatosunidade`, `cobrancas`, `planodecontas`) | ❌ 404; nomes provavelmente diferentes. Resolver por inspeção do tráfego |
| §7.2 — **existe filtro server-side por CNPJ?** | ⛔ Não conclusivo. **É a maior decisão de arquitetura da Fase C** |
| §7.3 — formato do anexo | ⚠️ Campo `arquivos` achado, formato não classificado |
| §7.5 — paginação | ⛔ Não conclusivo (baseline de 1 registro) |
| §7.6 — lote | ⬜ Deferido (depende de escrita) |
| §7.7 — `DD/MM` × `MM/DD` | ⚠️ Só formato com barra observado; ambiguidade não resolvível na leitura |
| §7 ⭐ — regra de associação | ⬜ Não executada |

### 5.3 Decisões humanas (H1–H8)

**Todas seguem abertas.** O documento original marcava **H3** (uma ou várias administradoras) e
**H7** (taxonomia de tipos) como "responder antes de escrever a Fase B" — nenhuma foi respondida.
H7 agora bloqueia a montagem da amostra.

### 5.4 Dívidas de documentação

- **O estudo da Fase A não foi atualizado.** Continua com 21 tags `[HIP]` e pelo menos 5 pontos
  hoje desatualizados. Ver o aviso no §0 do [`RELATORIO-ACHADOS.md`](../fase-b-spike/achados/RELATORIO-ACHADOS.md).
- **O roadmap visual está desatualizado.** Marca a Fase B como bloqueada por falta de credencial;
  a credencial chegou e as Fases 0–3 rodaram.
- **O README do spike** menciona um `.env.example` local que não existe (as variáveis foram para
  o `.env.example` da raiz).

---

## 6. Como analisar os resultados

### Rodar

```bash
# 1) Sanidade offline — sem rede, sem credencial (28 checagens)
python3 "docuparse-project/docs/superlogica/api integration plan/fase-b-spike/ferramenta/discovery_spike.py" --self-test

# 2) Smoke check — só o endpoint condominios
./run_script.sh python3 "docuparse-project/docs/superlogica/api integration plan/fase-b-spike/ferramenta/discovery_spike.py" --test-mode -v

# 3) Descoberta completa (fases 0–3)
./run_script.sh python3 "docuparse-project/docs/superlogica/api integration plan/fase-b-spike/ferramenta/discovery_spike.py" -v

# 4) + Fase 4, quando houver amostra
./run_script.sh python3 "docuparse-project/docs/superlogica/api integration plan/fase-b-spike/ferramenta/discovery_spike.py" --sample amostra.json -v
```

Se der `ERRO: defina SL_APP_TOKEN e SL_ACCESS_TOKEN`, o `.env` não carregou — confira as
variáveis `SL_*` no `.env` da raiz.

### Ler as saídas

| Arquivo | Para quê |
|---|---|
| `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/RELATORIO-ACHADOS.md` | **Leia primeiro.** Versão gerada, da última execução |
| `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/achados.json` | Achados completos, estruturados. Onde conferir qualquer número |
| `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/achados.csv` | Uma linha por controller — visão rápida de existe/não existe |
| `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/associacao.csv` | Uma linha por documento. **Só existe se a Fase 4 rodou** |

> O `RELATORIO-ACHADOS.md` **versionado** (nesta pasta) é curado à mão a partir dessas saídas e
> é o que persiste. O de `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/` é descartável e sobrescrito a cada execução.

### Interpretar — quatro armadilhas

1. **`exists: false` não significa "endpoint não existe".** Pode ser parâmetro obrigatório
   faltando. Confira `requer_param` e `body_error` no mesmo achado.
2. **HTTP 200 pode carregar erro.** O corpo pode trazer `msg` ou `status ≥ 100`. Olhe sempre
   `body_error`, não só `http_status`.
3. **Conclusão "não conclusiva" é resultado, não falha.** O filtro e a paginação vieram assim de
   propósito: com 1 condomínio, afirmar qualquer coisa seria falsa confiança.
4. **Nome de campo vem de heurística.** `campo_cnpj_condominio` e `campo_id_condominio` são
   palpites com boa pontuação, não fatos. Confirme por inspeção do tráfego do ERP; se errar,
   fixe com `SL_FIELD_CNPJ` / `SL_FIELD_ID`.

### Quando a Fase 4 rodar, olhar nesta ordem

1. **`index_size`** — bate com a carteira real? Se não, a credencial não vê tudo e **todo o
   resto está corrompido**.
2. **`% sem CNPJ` + `% CNPJ inválido`** — qualidade de extração do DocuParse.
3. **`cobertura`** — quanto da amostra a regra sequer alcança.
4. **`% ERRADO`** — o número de risco. Se > 0, bloqueador até ser entendido caso a caso.
5. **`go_no_go`** — se disser `RETIDO`, o ambiente não sustenta a conclusão; não force.

---

## 7. Próximo passo recomendado

Sondar o conteúdo do campo `arquivos` de uma despesa e classificar o formato. É **um `GET`**,
não depende de credencial nova nem de decisão de terceiros, e é o que destrava a montagem da
amostra.

Em paralelo, dois pedidos que dependem de outras pessoas e têm prazo longo: **H7** com a equipe
DocuParse e o **acesso à carteira completa** com quem administra a licença.

---

## 8. Invariantes — o que não pode ser violado

Valem para qualquer trabalho futuro nesta linha:

- **READ-ONLY absoluto.** Só `GET`, por guarda no cliente HTTP. Nenhuma execução altera o ERP.
- **PII e credenciais mascaradas** em toda saída persistida.
- **Nenhum limiar de auto-confirmação embutido.** A ferramenta mede e reporta; a política é
  decisão humana (H5).
- **O gabarito nunca sai da chave testada.** Obter `condominio_esperado_id` casando CNPJ
  produziria a resposta com a mesma régua sob avaliação.
- **O `cnpj_papel_condominio` sai do PDF, via DocuParse.** Tirá-lo dos campos da API testaria o
  ERP contra o ERP.
- **Fase não executada é declarada, nunca preenchida** com dado inventado.
