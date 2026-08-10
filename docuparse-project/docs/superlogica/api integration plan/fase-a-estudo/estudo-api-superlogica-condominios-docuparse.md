# Estudo exploratório — API Condomínios (Superlógica) × DocuParse — **Fase A**

> **O que é este documento (Fase A):** entendimento do problema + `Specify` (comportamento observável, o *quê* e o *porquê*), com base no que foi levantado e nos ajustes já feitos. **Não** é um passo a passo executável — isso é a Fase B.
>
> **Mapa das fases (spec-kit):**
> - **Fase A — este documento.** Entendimento + `Specify`. Define o problema, as entidades, o fluxo *provisório* de associação e o que ainda está em aberto.
> - **Fase B — plano de um *spike* de descoberta descartável** (`Plan`/`Tasks`). Um script Python de sondagem que roda uma **etapa de validação pré-execução**: bate na API real para converter as hipóteses **[HIP]** em fato, e testa com calma a regra central de associação antes de firmá-la. O spike **não** é a integração final; é o que responde as dúvidas.
> - **Fase C — o `Specify` real da integração**, alimentado pelo que o spike descobrir.
>
> **Convenção de confiança** (a regra aqui é *não inventar*):
> - **[DOC]** — fato confirmado em fonte oficial (doc da API, central de ajuda, páginas do produto).
> - **[PROD]** — confirmado pela equipe do DocuParse / dono do produto.
> - **[IND]** — indício de terceiro / wrapper / versão legada; provável, mas não é a doc oficial do `condor` v2.
> - **[HIP]** — hipótese a validar. Dois trilhos de resolução: **(via API)** na etapa pré-execução da Fase B; **(humano)** decisão de produto/negócio — ver §8 e o arquivo `pontos-a-esclarecer-validacao-humana.md`.
>
> Nada marcado **[HIP]** vira código sem verificação. Paths e nomes de campo exatos do `condor` v2 **não** foram confirmáveis pelas fontes indexadas (a doc é um Postman Documenter renderizado via JS), então aparecem como **[HIP] (via API)**.

---

## 1. Critérios de busca

Partindo do output do DocuParse (CPF, CNPJ, dados bancários, valores, localidade, empresa, nomes, remetentes, fornecedores, datas) e do objetivo (documento → condomínio), o que importa é responder:

1. **Qual campo extraído identifica o condomínio?** Não é o fornecedor. **[DOC]** O cadastro de fornecedores é *compartilhado por toda a carteira* — um mesmo fornecedor presta serviço a vários condomínios —, então o CNPJ/nome do fornecedor identifica o *prestador*, não o *condomínio*. O condomínio é uma pessoa jurídica com **CNPJ próprio** e aparece no documento como a *parte que paga/recebe*:
   - **Boleto (conta a pagar):** condomínio = **pagador/sacado**.
   - **Nota Fiscal de serviço:** condomínio = **tomador**.
   - **Conta de consumo (água/luz/gás):** condomínio = **titular / endereço da instalação**.

   **[PROD] Boa notícia para o desenho:** o DocuParse já entrega o CNPJ **com o papel semântico embutido** por tipo de documento (ex.: para NF, `cnpj_tomador` e `cnpj_fornecedor`). Ou seja, *não há passo de desambiguação* — para cada tipo, já se sabe qual CNPJ é o "lado condomínio". Isso simplifica o matching.

   → **Chave de associação candidata:** CNPJ do papel-condomínio (`cnpj_tomador`, pagador, titular…) ↔ CNPJ do condomínio no cadastro do Superlógica. **⚠️ Esta regra ainda não está firmada — é hipótese a testar (ver §5).**

2. **Chaves secundárias** (quando o CNPJ falha — OCR ruim, documento sem CNPJ do condomínio): endereço/CEP e nome/razão social do condomínio.

3. **Identificadores a obter** para "fechar o ciclo": `id_condominio` (PK) e — se o destino for lançar despesa — `id_fornecedor` e `id` do plano de contas.

4. **A API valida ou só consulta?** **[HIP]** Não há indício de endpoint que receba "o documento" e valide. Validação real = *ler as coleções cadastrais e reconciliar localmente*. Escrita (lançar despesa) é *ação*, não validação.

**Resumo do que procuramos:** os endpoints que (a) listam **condomínios com CNPJ/endereço** (o núcleo), (b) listam **fornecedores**, (c) recebem o **lançamento de despesa**, (d) expõem o **plano de contas**. O resto é secundário para *este* objetivo.

---

## 2. Escopo refinado

**Entra (essencial):** Condomínios (identificação — o coração), Fornecedores (reconciliar prestador + `id_fornecedor`), Despesas (destino do documento financeiro), Plano de Contas (categorização).

**Entra (secundário — só se o DocuParse tratar esses casos):** Unidades/Condôminos (só quando o documento é dirigido a uma *unidade específica*, não à conta do condomínio); Receitas/Cobranças (se processar boletos de *entrada*).

**Fica de fora (por ora):** assembleias, comunicados, reservas, conciliação bancária, EFD-Reinf, previsões orçamentárias.

**O que faltava no rascunho original e já foi incorporado:**
1. Distinção **fornecedor-compartilhado × despesa-por-condomínio** **[DOC]** — redefine a chave de associação (não é o fornecedor).
2. **Classificação do tipo de documento como passo 0** — determina qual campo é o papel-condomínio. **[PROD]** já resolvido na origem (CNPJ sai rotulado por papel).
3. **Plano de contas** como entidade de categorização.
4. Questão dos **anexos** (subir o PDF original junto da despesa) — a validar (§7).

**Premissa de cardinalidade [PROD]:** um documento mapeia para **um** condomínio; **vários** documentos podem pertencer ao mesmo condomínio (N:1, tranquilo — processa por documento). Se um *lote/arquivo* pode conter documentos de condomínios diferentes, isso depende de quais tipos o DocuParse processa → §8 (H7).

---

## 3. Endpoints e entidades relevantes

> **Módulos** = **[DOC]** (home da central de ajuda). **Padrão de URL** `https://api.superlogica.net/v2/condor/CONTROLLER/ACTION` = **[DOC]**. **Nomes de controller/action** = **[HIP] (via API)** — nomenclatura provável, a confirmar no spike.

| Endpoint/Entidade (controller provável) | O que expõe | Utilidade para o DocuParse | Prioridade | Confiança |
|---|---|---|---|---|
| **Condomínios** (`condor/condominios` [HIP]) | `id`, nome/razão social, **CNPJ**, endereço/CEP, responsável | **Núcleo da associação.** Casar CNPJ extraído → `id_condominio` | 🔴 Máxima | Módulo [DOC]; path [HIP] |
| **Fornecedores** (`condor/fornecedores` [HIP]) | Cadastro **compartilhado**: `id`, nome, CNPJ/CPF, dados bancários | Reconciliar emitente/beneficiário; obter `id_fornecedor`; detectar fornecedor novo | 🔴 Alta | Compartilhamento [DOC]; path [HIP] |
| **Despesas** (`condor/despesas` [HIP]) | Contas a pagar por condomínio: valor, vencimento, fornecedor, categoria, retenções, anexos(?) | **Destino do output.** Lançar despesa a partir dos campos; checar duplicidade | 🔴 Alta | Módulo [DOC]; path/campos [HIP] |
| **Plano de Contas** (`condor/planodecontas` [HIP]) | Contas contábeis do condomínio | Mapear categoria (água/luz/serviço) → conta; `id` da conta p/ despesa | 🟡 Média | Módulo [DOC]; path [HIP] |
| **Unidades** (`condor/unidades` [HIP]) | Frações/unidades, frações de rateio, indexadores | Só se o doc for de uma unidade específica | 🟢 Condicional | Frações [DOC]; path [HIP] |
| **Condôminos / Contatos de unidade** (`condor/condominos`/`contatosunidade` [HIP]) | Ocupantes (proprietário/inquilino/imobiliária) + histórico entrada/saída | Idem acima; casar CPF/nome de morador | 🟢 Condicional | Histórico [DOC]; path [HIP] |
| **Receitas / Cobranças** (`condor/cobrancas` [HIP]) | Boletos/cobranças emitidas | Só se processar documentos de *receita* | 🟢 Condicional | Módulo [DOC]; path [HIP] |
| **Notas Fiscais** (`condor/notafiscal` [HIP]) | Emissão/consulta de NF | Verificar; provavelmente NF de *saída* | ⚪ A verificar | [HIP] |

**Modelagem (indícios):**
- **[IND]** Integração de terceiro (UrbanBee) trata condomínio com `superlogica_id` e unidades com *tipos de ocupação* ("Proprietário Residente", "Inquilino") normalizados p/ `owner`/`tenant` → **unidade tem tipo/ocupação**, coerente com o **[DOC]** "histórico de contatos de unidades (inquilinos, imobiliárias e proprietários com data de entrada/saída)".
- **[IND/HIP]** Nomes de campo seguem *notação húngara* (`ST_` string, `DT_` data, `ID_` id, `TX_` texto) + nome + sufixo de tabela. Os sufixos exatos do `condor` (ex.: `_COND`) precisam ser confirmados.

---

## 4. Relacionamentos entre entidades

```
Administradora (carteira)
   │
   ├── Fornecedores ....................... [DOC] cadastro COMPARTILHADO na carteira
   │        (usados por N condomínios)
   │
   └── Condomínio (id_condominio, CNPJ) ... unidade de escopo de quase tudo
            │
            ├── Unidades / Frações
            │        └── Contatos da unidade (proprietário / inquilino / imobiliária,
            │                                  com histórico entrada/saída)  [DOC]
            │
            ├── Plano de Contas (contábil)
            │
            ├── Despesas (contas a pagar) ── referenciam ──► Fornecedor  [DOC: lançamento é POR condomínio]
            │        └── categorizadas por ──► Plano de Contas
            │        └── anexos? (PDF original)  [HIP]
            │
            └── Receitas / Cobranças (boletos) ──► Unidade/Condômino
```

**Ponto-chave:** a **Despesa** conecta *condomínio + fornecedor + plano de contas + valores/datas* — exatamente os campos do DocuParse. Mas o fornecedor "atravessa" vários condomínios, então **a despesa é sempre ancorada no `id_condominio`**, e é esse id que precisa ser resolvido primeiro.

---

## 5. Fluxo proposto de identificação do condomínio *(provisório — depende de validação)*

> ⚠️ **A REGRA CENTRAL AINDA NÃO ESTÁ FIRMADA.** A hipótese *"o CNPJ do papel-condomínio (tomador/pagador/titular) casa 1:1 com o cadastro de condomínios"* precisa ser **testada com calma numa seção dedicada do spike (Fase B)** antes de virar regra. Pontos a investigar antes de confiar:
> - documentos em que o condomínio **não** aparece com CNPJ próprio (ex.: conta de consumo em nome da administradora, do síndico ou de terceiro);
> - CNPJ do condomínio **ausente ou ilegível** no documento;
> - condomínios com **CNPJs relacionados/parecidos**, ou mudança de CNPJ ao longo do tempo.
>
> **Risco se errar:** associar um documento ao **condomínio errado** num sistema financeiro tem impacto **financeiro e jurídico** (dinheiro lançado na conta errada). Por isso o matching não é auto-confirmado até ser validado, e a *política* de tolerância é decisão humana (§8, H5). **Enquanto não validada, o fluxo abaixo é provisório.**

**Passo 0 — Tipo do documento.** O DocuParse já classifica; isso define qual campo é o papel-condomínio (boleto→pagador; NF→tomador; consumo→titular/endereço).

**Passo 1 — CNPJ do papel-condomínio.** **[PROD]** já vem rotulado (ex.: `cnpj_tomador`) — **sem desambiguação**. Normalizar (tirar máscara) e validar dígitos verificadores **localmente**. Guardar nome e endereço/CEP como fallback.

**Passo 2 — Índice de condomínios.** **[HIP] (via API)** `GET condor/condominios` → todos da carteira (paginado, §7). Construir índice local `{ CNPJ_normalizado → (id_condominio, nome, endereço) }`. *Recomendação:* cachear em Postgres e sincronizar periodicamente — a carteira muda pouco; evita bater na API por documento.

**Passo 3 — Casar.**
- **Match exato por CNPJ** → `id_condominio`. Alta confiança (*sujeito à validação da regra*).
- **Sem CNPJ ou sem match** → fallback fuzzy por (nome + endereço/CEP) → candidatos → **revisão humana**.

**Passo 4 (opcional) — Enriquecer fornecedor.** **[HIP] (via API)** `GET condor/fornecedores` → casar CNPJ do emitente (`cnpj_fornecedor`) → `id_fornecedor`. Não encontrado → fornecedor novo (criar ou sinalizar).

**Passo 5 (opcional) — Categorizar.** **[HIP] (via API)** `GET condor/planodecontas` → mapear categoria → `id` da conta.

**Passo 6 — Saída.** `{ id_condominio, id_fornecedor?, id_conta?, valor, vencimento, campos_extraídos, doc_original }`. Se o destino for **lançar despesa**: **[HIP] (via API)** `POST condor/despesas`, **com human-in-the-loop** (§8, H1).

**Identificadores-chave:**

| Identificador | Papel |
|---|---|
| `id_condominio` | PK do condomínio; ancora tudo |
| CNPJ do condomínio | **chave de matching** (regra a validar) |
| `id_fornecedor` (+ CNPJ) | referência para despesa; cadastro compartilhado |
| `id` do plano de contas | categoria contábil da despesa |
| `id_unidade` | só quando o doc é de uma unidade específica |

---

## 6. A API como validadora

**O que dá para validar/enriquecer** (por *leitura + reconciliação*, não por "endpoint validador") — **presume a regra de associação já validada (§5)**:

- **CNPJ do condomínio** — validar contra a lista de condomínios (fonte da verdade). Se não existe na carteira → sinalizar. Dígitos verificadores: **local**.
- **Fornecedor** — confirmar pelo CNPJ; se existe, puxar dados canônicos e comparar com o que o OCR extraiu (detecta erro de extração). Se não, é novo.
- **Plano de contas / categoria** — validar se a categoria inferida existe para o condomínio.
- **Coerência de valores/datas** — regra local; ao lançar despesa a API aplica as próprias validações **[HIP]** (formato de data `MM/DD/AAAA` **[DOC]**, campos obrigatórios).

**O que (provavelmente) *não* dá:**
- **[HIP]** Enviar o blob do documento e receber "válido/pertence ao condomínio X". Não há indício. A validação é responsabilidade da reconciliação.
- Autenticidade fiscal (SEFAZ, banco) — fora do escopo do Superlógica.

**Permissões [DOC]:** o par `app_token`/`access_token` herda as permissões do usuário que criou o token; sem permissão, a API **bloqueia a consulta**. Para o DocuParse enxergar toda a carteira, o token precisa ser criado por um usuário com acesso a todos os condomínios.

---

## 7. Validação via API — etapa pré-execução (Fase B)

> Estas são as perguntas que **só a API responde**. Viram os primeiros `Tasks` do spike: uma bateria de `GET` (read-only, seguros) que confirma existência, path, campos e formato **antes** de qualquer lógica de negócio. Cada item aqui é um **[HIP] (via API)**.

1. **Paths e actions exatos do `condor` v2** para: condomínios, unidades, condôminos/contatos, fornecedores, despesas, cobranças, plano de contas, notas fiscais, **anexos**.
2. **Campo do CNPJ do condomínio** (nome exato) e **se existe filtro server-side** (ex.: `GET condor/condominios?CNPJ=...` ou `?pesquisa=...`). **Bifurcação de arquitetura:** se o filtro *não* existir, é obrigatório sincronizar a lista inteira localmente — e aí frescor/webhook deixa de ser opcional.
3. **Anexos:** a despesa aceita o PDF original? Formato (URL / base64 / multipart)? Decide se o DocuParse pode *arquivar o documento fonte* no próprio ERP.
4. **Modelo de autenticação e de erro:** tokens são stateless por requisição ou há sessão? Expiram? Um 401 faz o quê? O erro vem por **HTTP status** ou por **envelope no corpo** (a v1 usava um campo `status` onde ≥100 = erro)? Define a camada de auth/retry do script.
5. **Paginação e limites:** a v1 usa `pagina`/`itensPorPagina`, default ~20 itens **[IND, v1]**; confirmar no v2. **Rate limits não são públicos** — perguntar ao Superlógica antes de desenhar sincronização em lote.
6. **Lote:** o padrão de múltiplas requisições num array `params` é **[IND, v1]**; confirmar se o v2 mantém e o teto por lote.
7. **Formato de data:** `MM/DD/AAAA` é **[DOC]** no envio; confirmar se vale para *todos* os parâmetros e qual o formato **nas respostas** (bug clássico: `03/05/2026` passa como mês errado).
8. **Unidades/condôminos:** nomes de campo e como a ocupação (proprietário/inquilino) é representada (indícios **[IND]** apontam tipo + ocupação).
9. **⭐ Validação da regra de associação (seção dedicada do spike):** com uma amostra real de documentos + a carteira, medir se o match por CNPJ do papel-condomínio realmente acerta o condomínio — taxa de acerto, falsos positivos, casos sem CNPJ. **É o teste que decide se a regra do §5 pode ser firmada.**

**Dica de descoberta (rápida e barata) [DOC]:** a interface do ERP usa a mesma API. Simular a operação na tela e inspecionar o tráfego de rede (aba *Network* / devtools) revela **path e payload exatos** — inclusive nomes de campo —, resolvendo a maioria dos itens acima em minutos. Se a coleção Postman oferecer "Run in Postman"/exportação, importe-a inteira. E criar um **App Token de teste** (plano Enterprise I+ **[DOC]**) num trial é a forma definitiva de confirmar.

---

## 8. Pontos a serem esclarecidos

Consolidação de tudo que ainda não está fechado. **Dois trilhos de resolução:**

- **Trilho técnico (via API)** → resolvido na etapa de validação pré-execução da Fase B. Detalhes na **§7**.
- **Trilho humano (decisão de produto/negócio)** → precisa de **validação humana**. Registro detalhado e persistente no arquivo separado **`pontos-a-esclarecer-validacao-humana.md`**. Índice abaixo.

**Índice do trilho humano** (detalhe no arquivo separado):

| ID | Ponto a esclarecer | Bloqueia Fase B? |
|---|---|---|
| **H1** | Objetivo final: só identificar/arquivar × lançar despesa no ERP | Não |
| **H2** | Fonte da verdade / dono da escrita (provavelmente Superlógica) | Não |
| **H3** | Multi-tenancy no nível *administradora*: uma conta/token × várias | Parcial |
| **H4** | Volume da carteira (nº de condomínios) | Não |
| **H5** | Tolerância a erro de associação: limiar auto-confirma × revisão humana | Não |
| **H6** | Idempotência / duplicidade (não lançar 2×, inclusive já lançado manual) | Não |
| **H7** | Taxonomia completa de tipos de documento + papel-CNPJ por tipo | Parcial |
| **H8** | Transversais: LGPD (dados pessoais puxados) + trilha de auditoria da associação | Não |

> Os dois que mais convém responder **antes** de escrever a Fase B: **H3** (define arquitetura de credenciais) e **H7** (define a matriz de teste do spike, incl. a seção ⭐ de validação da regra).

---

### Fontes consultadas
- Documentação oficial da API Condomínios (padrão de URL, autenticação, headers, formato de data, case-sensitive) — `apicondominios.superlogica.com`.
- Central de ajuda Superlógica Condomínios (módulos; artigo de **Fornecedores** = cadastro compartilhado / despesa por condomínio; cadastro de App Token) — `condominios.superlogica.com/hc`.
- Páginas de produto/planos (frações de rateio, histórico de contatos de unidades, plano Enterprise para API completa) — `superlogica.com`.
- Wrapper Python `superlogica-api-wrapper` (PyPI) e artigos de integração — confirmam a gramática de URL e o modelo de tokens (namespace `financeiro`, análogo ao `condor`).
- Integração de terceiro (UrbanBee/Redocly) e doc legada v1 — indícios de modelagem e de lote/paginação (**tratados como [IND]**).
- Contrato de saída do DocuParse e premissas de negócio — **[PROD]** informado pela equipe.
