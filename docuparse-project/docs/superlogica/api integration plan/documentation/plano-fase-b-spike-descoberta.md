# Fase B — Plano do *spike* de descoberta (`Plan` + `Tasks`)

> **O que é (e o que não é):** este é o plano de um **spike de descoberta descartável** — um script Python de sondagem cujo único trabalho é **converter os `[HIP]` do §7 da Fase A em fato** e **testar a regra central de associação** antes de firmá-la. **Não é a integração.** O *script* é jogado fora; o que persiste é o **relatório de achados** que ele produz, e que vira insumo do `Specify` real (Fase C).
>
> **Rastreabilidade:** cada tarefa aponta o item do **§7 da Fase A** que ela resolve. A Fase 4 (⭐) corresponde ao §7 item ⭐ e ao bloco de risco do §5.
>
> **Convenção de confiança:** mesma da Fase A (`[DOC]` / `[PROD]` / `[IND]` / `[HIP]`). A saída do spike **reescreve** `[HIP] → [DOC]` (confirmado por teste) ou `[HIP] → [descartado]`.

---

## 1. Objetivo e não-objetivos

**Objetivo:** ao fim do spike, para cada `[HIP]` do §7 existir um status resolvido (confirmado / não-encontrado / diferente do esperado), e existir uma **decisão go/no-go sobre a regra de associação**, sustentada por métricas.

**Não-objetivos (ficam para a Fase C):**
- Não escreve nada no ERP. **Spike é 100% read-only** (só `GET`). O caminho de escrita (lançar despesa) é validado depois, num passo separado e explicitamente autorizado.
- Não implementa cache Postgres, retry robusto, fila, idempotência — são preocupações da integração, não da descoberta.
- Não decide o *limiar* de tolerância (H5): o spike **mede**; a política é humana.

---

## 2. Premissas assumidas (defaults de H1–H8)

> Assumidas para o spike **poder ser escrito e rodado** sem travar. Cada uma é marcada e aponta onde confirmar (ver `pontos-a-esclarecer-validacao-humana.md`).

| # | Premissa assumida no spike | Confirmar em |
|---|---|---|
| H1 | Escopo do spike = **descoberta read-only**; caminho de escrita fora | H1 |
| H2 | Superlógica é a **fonte da verdade** → o spike **lê** dela | H2 |
| H3 | **1 administradora / 1 par de tokens** (config única) | H3 |
| H4 | Volume **dezenas–centenas** → ainda assim testa paginação | H4 |
| H5 | **Nenhum** limiar assumido; o spike só reporta métricas | H5 |
| H6 | Idempotência **fora de escopo** (é escrita) | H6 |
| H7 | Amostra começa por **NF, boleto, conta de consumo** | H7 |
| H8 | **Minimizar PII**: amostra reduzida/anonimizada; logar as próprias ações | H8 |

---

## 3. Pré-requisitos para **rodar** (não só escrever)

> ⚠️ O plano abaixo pode ser *escrito* sem nada disto — mas sem estes insumos o spike **não roda**, e aí ele só *reformula* os `[HIP]` em vez de *resolvê-los*. São os primeiros bloqueios a destravar.

1. **Credencial de API** — um **App Token de teste** (`app_token` + `access_token`), criado por um usuário que **enxerga toda a carteira** `[DOC]` (senão a API filtra por permissão). Idealmente num **trial/sandbox** (plano Enterprise I+ `[DOC]`); se for contra produção, **só `GET`**.
2. **Amostra rotulada (ground truth)** para a Fase 4 — um conjunto de documentos **cujo condomínio correto já é conhecido**. Sem rótulo, a Fase 4 mede "casou/não casou", mas **não** "acertou/errou". *Caminho limpo:* pegar documentos **já corretamente arquivados manualmente** no ERP e usar essa associação como gabarito.
3. **Saída do DocuParse** para esses documentos — os campos extraídos com os papéis (`cnpj_tomador`, `cnpj_fornecedor`, pagador, titular…) `[PROD]`, dos tipos de H7.

---

## 4. Abordagem técnica (`Plan`)

- **Stack:** Python + `httpx` (ou `requests`); config por **variáveis de ambiente** (`SL_APP_TOKEN`, `SL_ACCESS_TOKEN`, `SL_BASE_URL`) — **nada de segredo hardcoded**.
- **Estrutura:** ferramenta modular de sondagem, descartável mas **re-executável** e **idempotente na leitura** (rodar de novo não muda nada no servidor).
- **Trilhos de segurança:** guarda rígida que **bloqueia qualquer método ≠ GET**; toda chamada é **logada** (endpoint, status, latência); **PII minimizada** nos logs/saídas (mascarar CPF/CNPJ além do necessário para o match).
- **Modos de execução:** *completo* (default) varre **todos** os controllers candidatos do §3 da Fase A e gera achados de cada um; *teste* (flag `--test-mode`) avalia **somente o endpoint `condominios`** e gera achados só dele — um smoke check rápido antes da varredura completa (detalhe em §4.1).
- **Saída (o que persiste):** dois artefatos, alinhados ao seu padrão CSV-intermediário —
  - `achados.json` / `achados.csv`: por endpoint → { path, status HTTP, envelope de erro?, campos descobertos, paginação, nota, **status do `[HIP]`** }.
  - `associacao.csv`: por documento → { doc, tipo, cnpj_papel_condominio, condominio_casado, condominio_esperado, resultado }.
  - `RELATORIO-ACHADOS.md`: leitura humana que **atualiza as tags de confiança** da Fase A e traz o **go/no-go** da regra.
- **Padrão de sonda por endpoint** (reutilizável):

```python
def probe(client, controller, params=None):
    # SÓ GET. Classifica: existe / não-encontrado / erro-auth / erro-envelope.
    r = client.get(f"/v2/condor/{controller}", params=params or {})
    body = safe_json(r)
    return {
        "controller": controller,
        "http_status": r.status_code,
        "body_status": dig(body, "status"),         # v1 usava 'status' no corpo (§7.4)
        "keys": sample_keys(body),                  # nomes de campo (notação húngara)
        "pagination_hint": detect_pagination(body), # §7.5
        "sample": redact(first_record(body)),       # 1 registro, PII mascarada
    }
```

### 4.1 Modos de execução

- **Completo (default):** o spike varre **todos** os controllers candidatos do §3 da Fase A (`condominios`, `unidades`, `condominos`/`contatosunidade`, `fornecedores`, `despesas`, `cobrancas`, `planodecontas`, `notafiscal`) e gera achados para cada um. Ou seja — respondendo diretamente à dúvida: **sim, no modo completo saem achados de todos os endpoints listados na Fase A.**
- **Teste (flag `--test-mode`):** a **primeira e única** coisa avaliada é o endpoint **`condominios`**. Só ele é sondado e só dele saem achados; as Fases 1–2 rodam restritas a `condominios` e a Fase 3 (que ataca `despesas`) é **pulada**. Serve como **smoke check**: confirma conectividade, autenticação, que o endpoint-núcleo responde e **descobre o nome do campo de CNPJ** — tudo antes de se comprometer com a varredura completa. Por que `condominios`? Porque é a entidade central da associação (§5): sem ela, o resto não importa.

**Uso recomendado:** rode `--test-mode` **primeiro**; com ele verde, rode o modo completo.

### 4.2 Glossário dos campos de achado

Cada bloco de achado (em `achados.json`) carrega os campos abaixo. O que cada um significa:

- **`http_status`** — o código HTTP da resposta (200, 401, 404…). É o sinal de erro/sucesso "padrão REST".
- **Envelope de erro (`body_status`)** — algumas APIs **não** sinalizam erro pelo HTTP status: retornam **HTTP 200 "OK" com o erro embutido no corpo JSON**, num "envelope" com um campo tipo `status`/`msg`/`erro`. A API **v1** do Superlógica fazia exatamente isso (`status` no corpo, valores ≥100 = erro). Isso importa porque um cliente que só olha o HTTP status trataria esse erro como sucesso e seguiria com dados vazios. Por isso o achado captura **os dois** (`http_status` **e** `body_status`); a Fase 0 (§7.4) determina qual padrão o **v2** usa.
- **Paginação (`pagination_hint`)** — endpoints que listam muitos registros não devolvem tudo de uma vez; devolvem em **páginas** (ex.: `?pagina=2&itensPorPagina=50`), em geral com metadados na resposta (total de registros, página atual, itens por página). O `pagination_hint` são esses metadados detectados — servem pra confirmar os **nomes dos parâmetros** de paginação e o **default** de itens por página (§7.5). É crítico porque, para montar o índice de condomínios (Fase 4), o spike precisa percorrer **todas** as páginas; errar os parâmetros = índice incompleto = associação furada.
- **`fields` / `sample`** — os nomes de campo reais descobertos no endpoint e 1 registro de exemplo, com PII mascarada.
- **Nota (`nota`)** — texto livre onde o spike registra **observações, ressalvas e limitações** daquela sonda em linguagem humana (ex.: "expiração de token não é verificável numa execução única"; "formato com barra não distingue DD/MM de MM/DD só na leitura"). Não é dado estruturado — é o "comentário do investigador" para quem lê o relatório entender o contexto e o que ainda precisa de confirmação.

---

## 5. Tarefas (`Tasks`)

> Ordenadas por dependência. Cada fase fecha um bloco do §7. **DoD** = *definition of done*.
>
> **No modo de teste (`--test-mode`, §4.1):** as Fases 1–2 rodam apenas sobre `condominios` e a Fase 3 é pulada — use-o como primeira execução (smoke check).

### Fase 0 — Setup & sonda de autenticação/erro → resolve §7.4
| Task | O que faz | DoD |
|---|---|---|
| 0.1 | Bootstrap: client `httpx`, config por env, guarda "GET-only", logger | Client sobe e recusa não-GET |
| 0.2 | Sonda de auth: um `GET` simples; observar se token é **stateless por requisição** ou exige sessão; se **expira** | Documentado: stateless? expira? |
| 0.3 | Sonda de erro: forçar 401 (token inválido) e um path inexistente; capturar se o erro vem por **HTTP status** ou por **envelope no corpo** (`status` ≥100?) | Modelo de erro descrito |

### Fase 1 — Descoberta de endpoints & campos → resolve §7.1, §7.2 (campo), §7.8
| Task | O que faz | DoD |
|---|---|---|
| 1.1 | Rodar `probe()` em cada controller candidato do §3 (condominios, unidades, condominos/contatosunidade, fornecedores, despesas, cobrancas, planodecontas, notafiscal). **No `--test-mode`: só `condominios`.** | Cada um: existe / não / erro |
| 1.2 | Para os que existem, **capturar nomes de campo** reais (notação húngara) e 1 registro mascarado | Lista de campos por entidade |
| 1.3 | **Descobrir o NOME do campo de CNPJ na resposta da API** (não o valor — o valor já vem do DocuParse). O nome exato desse campo no cadastro do condomínio é um `[HIP]`; a heurística acha-o varrendo os valores do registro atrás de uma string de 14 dígitos | Nome do campo de CNPJ do lado Superlógica identificado (ex.: `ST_CGC_CON`) |
| 1.4 | Nos não-encontrados, marcar para **descoberta manual via tráfego do ERP** (tarefa complementar) | Pendências registradas |

```python
# 1.3 — descobrir em QUAL campo da resposta da API mora o CNPJ do condomínio
# (retorna nomes de coluna, não valores). Usado 1x na descoberta; depois o nome vira fixo.
def find_cnpj_field(record):
    for k, v in record.items():
        if re.fullmatch(r"\D*\d{14}\D*", str(v) or ""):   # valor com cara de CNPJ (14 dígitos)
            yield k                                        # k = nome do campo (ex.: ST_CGC_CON)
```

> **Por que esta tarefa existe (há dois CNPJs no problema):** o CNPJ do **documento** já vem do DocuParse, rotulado por papel (`cnpj_tomador` etc.) — esse é o *valor a procurar*. O que falta é saber **em qual coluna** o `GET condor/condominios` guarda o CNPJ **do condomínio** — o nome dessa coluna é `[HIP]`. A heurística descobre esse nome (ex.: `ST_CGC_CON`); só então dá para montar o índice `{ CNPJ → id_condominio }` e casar um lado contra o outro. É um atalho de descoberta usado uma vez — a inspeção do tráfego do ERP (tarefa complementar) confirma o mesmo nome.

### Fase 2 — Mecânica: filtro, paginação, lote, data → resolve §7.2 (filtro), §7.5, §7.6, §7.7
| Task | O que faz | DoD |
|---|---|---|
| 2.1 | **Filtro server-side por CNPJ:** testar params candidatos (`?CNPJ=`, `?pesquisa=`, `?ST_CGC_...=`) com um CNPJ conhecido; ver se **estreita** o resultado | **Bifurcação decidida:** filtro existe? (se não → sync local obrigatório) |
| 2.2 | **Paginação:** confirmar params (`pagina`/`itensPorPagina` da v1 `[IND]`) e o **default** de itens por página | Params + default confirmados |
| 2.3 | **Lote:** testar o array `params` (padrão v1 `[IND]`) num `GET`; achar o **teto** por lote | Suporte + teto (ou "não") |
| 2.4 | **Data:** observar o formato **nas respostas**; se houver `GET` com filtro de data, testar `MM/DD` vs `DD/MM` contra registro conhecido | Formato de envio **e** de resposta |
| 2.5 | **Rate limit:** subir a cadência devagar e observar 429/headers; **na dúvida, throttle conservador** | Limite observado (ou "não público") |

### Fase 3 — Sonda de anexos (read-only) → resolve §7.3
| Task | O que faz | DoD |
|---|---|---|
| 3.1 | Ler uma **despesa existente que tenha anexo** e inspecionar o campo: o PDF vem como **URL / base64 / referência**? | Formato de anexo na **leitura** documentado |
| 3.2 | Registrar o que **falta** para confirmar a **escrita** de anexo (só se resolve escrevendo → deferido para passo autorizado) | Lacuna de escrita anotada |

### Fase 4 — ⭐ Validação da regra de associação → resolve §7 (⭐) e o risco do §5
> **A tarefa que decide se a regra do §5 pode ser firmada.** Não pule direto para a integração sem isto.

| Task | O que faz | DoD |
|---|---|---|
| 4.1 | Construir o **índice de condomínios** `{ CNPJ_normalizado → (id, nome, endereço) }` a partir do `GET condor/condominios` (paginado) | Índice montado |
| 4.2 | Para cada documento da **amostra rotulada**, pegar o **CNPJ do papel-condomínio** `[PROD]`, normalizar, validar DV **localmente**, e casar no índice | `associacao.csv` gerado |
| 4.3 | **Medir**: % match exato por CNPJ; **% correto entre os que casaram** (vs. gabarito); % sem-CNPJ; % ambíguo/errado. Classificar os **modos de falha** (consumo em nome de terceiro, CNPJ ausente/ilegível, CNPJs parecidos) | Métricas + taxonomia de falhas |
| 4.4 | Testar o **fallback fuzzy** (nome + endereço/CEP) nos que falharam por CNPJ; medir quanto recupera | Ganho do fallback medido |
| 4.5 | **Go/No-Go:** relatar se a regra é confiável, em que faixa de confiança, e para quais tipos ela quebra. Se a precisão for baixa → a saída é **repensar a chave** (não firmar) | Recomendação explícita + números |

```python
# 4.3 — esqueleto das métricas (gabarito = condomínio correto conhecido)
total      = len(amostra)
casou      = [d for d in amostra if d["condominio_casado"]]
corretos   = [d for d in casou   if d["condominio_casado"] == d["condominio_esperado"]]
sem_cnpj   = [d for d in amostra if not d["cnpj_papel_condominio"]]
# precisão do match = corretos / casou  ; cobertura = casou / total
```

### Fase 5 — Consolidação
| Task | O que faz | DoD |
|---|---|---|
| 5.1 | Gerar `RELATORIO-ACHADOS.md`: por item do §7, o status resolvido (`[HIP]→[DOC]`/descartado) | Relatório completo |
| 5.2 | Anexar o **go/no-go** da regra (Fase 4) e a **bifurcação do filtro** (2.1) | Decisões registradas |
| 5.3 | Listar o que **sobrou** para a Fase C (ex.: validação de escrita, anexos-escrita) | Backlog p/ Fase C |

### Complementar (manual) — Inspeção do tráfego do ERP → acelera §7.1/§7.2 `[DOC]`
Simular na tela do ERP as operações (listar condomínios, abrir uma despesa) e ler a aba **Network** do navegador: revela **path e payload exatos**, inclusive nomes de campo. Resolve os "não-encontrados" da Fase 1 em minutos e serve de **conferência cruzada** dos achados do script.

---

## 6. Critérios de aceite do spike (DoD global)
- [ ] **Smoke check com `--test-mode` passou** (`condominios` responde, autentica, campo de CNPJ descoberto) — pré-condição antes da varredura completa.
- [ ] Todo item do §7 tem status resolvido no `RELATORIO-ACHADOS.md`.
- [ ] Bifurcação do filtro por CNPJ (2.1) **decidida** — define se sync local é obrigatório.
- [ ] Modelo de auth e de erro (Fase 0) **descrito** — base da camada de auth/retry da Fase C.
- [ ] Regra de associação com **go/no-go + métricas** (Fase 4) — não fica "no achismo".
- [ ] `achados.csv` + `associacao.csv` + relatório **persistidos** (o script pode ser descartado).

---

## 7. Riscos e saídas possíveis
- **A regra pode falhar** (precisão baixa na Fase 4). Isso **não é fracasso do spike** — é o resultado mais valioso: significa repensar a chave (endereço? outro identificador? combinação?) **antes** de construir a integração. O spike tem que ser honesto sobre isso.
- **Sem filtro server-side** → confirma a arquitetura de **sincronização local** da carteira (e reabre frescor/webhook, §7.2).
- **Rate limit desconhecido** → throttle conservador por padrão; ajustar quando confirmado.
- **Sem credencial/sandbox ou sem amostra rotulada** → o spike não roda; priorizar destravar os pré-requisitos do §3.

---

## 8. Como isto alimenta a Fase C
O `RELATORIO-ACHADOS.md` reescreve os `[HIP]` da Fase A em fato, e o **go/no-go da regra** + os **endpoints/campos confirmados** viram as entradas do `Specify` real da integração (Fase C): comportamento observável ("dado um documento do tipo X, o sistema associa ao condomínio por CNPJ com confiança ≥ *limiar de H5*, senão envia para revisão"), critérios de aceite testáveis, e o desenho read-only × escrita já sustentado por evidência — não por suposição.
