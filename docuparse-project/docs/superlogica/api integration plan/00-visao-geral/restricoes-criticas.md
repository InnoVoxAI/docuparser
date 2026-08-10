# Restrições críticas e riscos conhecidos

_Atualizado em 2026-08-10 · integração DocuParse × API Condomínios (Superlógica)_

> **Para que serve:** reunir num lugar só as questões que **travam ou condicionam** as próximas
> fases. Cada item diz o que é, **onde ocorre**, **o que trava** e **como resolver**.
>
> Não é lista de bugs nem backlog. É o conjunto de coisas que, se ignoradas, produzem vazamento
> de dado, decisão errada de arquitetura ou — o pior caso — **dado financeiro errado sem
> sintoma visível**.
>
> Leia junto com o [estado atual](estado%20atual%20discovery%20superlogica.md) (onde estamos) e
> o [relatório de achados](../fase-b-spike/achados/RELATORIO-ACHADOS.md) (o que foi medido).

## Como ler

| Severidade | Significado |
|---|---|
| 🔴 **Crítica** | Vaza segredo/PII ou corrompe dado financeiro **sem sintoma**. Endereçar antes da Fase C |
| 🟠 **Alta** | Decide arquitetura ou pode gerar retrabalho caro |
| 🟡 **Média** | Precisa de resposta, mas há contorno |

| Origem | Significado |
|---|---|
| **Fornecedor** | Defeito ou limitação do Superlógica. Não controlamos — mas lidamos |
| **Nossa** | Está no nosso código ou no nosso desenho. Inteiramente nossa |
| **Ambiente** | Credencial, licença ou dados disponíveis |
| **Método** | Armadilha de como medimos ou validamos |

## Índice

| # | Restrição | Sev. | Origem | Trava |
|---|---|---|---|---|
| [R-01](#r-01) | Credenciais de terceiros na resposta de `condominios` | 🔴 | Fornecedor | Sincronização local |
| [R-02](#r-02) | PII não mascarada nos artefatos e na ingestão | 🔴 | Nossa | Conformidade LGPD |
| [R-03](#r-03) | Permissão parcial filtra a carteira **em silêncio** | 🔴 | Fornecedor | Confiabilidade de tudo |
| [R-04](#r-04) | `DD/MM` × `MM/DD` indistinguível na leitura | 🔴 | Fornecedor | Datas financeiras |
| [R-05](#r-05) | Nomes de campo vêm de heurística | 🟠 | Método | Índice da Fase 4 |
| [R-06](#r-06) | Gabarito circular invalida a medição | 🟠 | Método | Go/no-go |
| [R-07](#r-07) | Filtro server-side por CNPJ indefinido | 🟠 | Ambiente | Arquitetura da Fase C |
| [R-08](#r-08) | `500` não é sinal de retry | 🟠 | Fornecedor | Camada de auth/retry |
| [R-09](#r-09) | Rate limit desconhecido e sem cabeçalhos | 🟠 | Fornecedor | Estratégia de sincronização |
| [R-10](#r-10) | Carteira de 1 condomínio | 🟠 | Ambiente | Go/no-go, filtro, paginação |
| [R-11](#r-11) | Expiração de credencial não observável | 🟡 | Fornecedor | Renovação de token |
| [R-12](#r-12) | `notafiscal` vaza erro de SQL | 🟡 | Fornecedor | Uso do endpoint |
| [R-13](#r-13) | Caminho de escrita totalmente desconhecido | 🟡 | Escopo | H1 e Fase C |
| [R-14](#r-14) | CNPJ alfanumérico não suportado | 🟡 | Nossa | Quebra futura |

---

## A. Segurança e privacidade

### R-01 — Credenciais de terceiros na resposta de `condominios` {#r-01}

🔴 **Crítica** · Origem: **Fornecedor** (mas o risco vira nosso na persistência)

**O que é.** `GET condor/condominios` devolve **29 campos com sufixo `_usu`**, resultado de um
`LEFT JOIN` com a tabela de usuários embutido na resposta. Entre eles: `st_senha_usu`,
`st_apptoken_usu`, `st_accesstoken_usu`, `st_chavegruvi_usu`, `st_ipsliberados_usu`.

**Onde ocorre.** Endpoint [`condominios`](../endpoints/condominios.md), na resposta de listagem.

**Estado da evidência.** Na única carteira acessível os 29 campos vêm **vazios** — o condomínio
não tem usuário de integração vinculado. Mas **o schema foi projetado para carregá-los**: não é
sobra, é join. Não confirmamos se algum dia vêm preenchidos, nem se `st_senha_usu` seria hash ou
texto puro.

**O que trava.** Nada hoje. O risco materializa na Fase C: se a bifurcação do [R-07](#r-07)
resolver por **sincronização local**, esses campos entram no nosso Postgres — e passamos a
armazenar credenciais de outra gente. Vazamento nosso é responsabilidade nossa,
independentemente de quem expôs primeiro.

**Como resolver.**

1. **Allowlist na fronteira de ingestão, não denylist.** Dos 109 campos, a integração precisa de
   ~4 (`id_condominio_cond`, `st_cpf_cond`, `st_nome_cond`, `fl_ativo_cond`). Declare esses e
   descarte o resto **por padrão**. Um denylist falha aberto no dia em que o Superlógica
   adicionar `st_novaCredencial_usu`; um allowlist falha fechado.
   > O spike usa denylist por regex (`token|senha|secret|chave`). Serve para ferramenta
   > descartável — **não serve para produção**.
2. **Nunca logar resposta crua.** Um `logger.debug(response.json())` numa investigação manda o
   token para o agregador de logs, onde a retenção é longa e o acesso é mais frouxo que o do banco.
3. **Reportar ao Superlógica.** É defeito deles e devem saber. Cria registro de que
   identificamos e comunicamos.
4. **Confirmar quando a carteira crescer.** Se vier token real preenchido, muda de categoria e
   vira comunicação formal com prazo.

---

### R-02 — PII não mascarada nos artefatos e na ingestão {#r-02}

🔴 **Crítica** · Origem: **Nossa**

**O que é.** A ferramenta mascara CPF/CNPJ **por formato do valor** (11 e 14 dígitos). E-mail,
telefone, endereço e RG não têm formato que essa heurística pegue, e passam **íntegros** para os
artefatos.

**Onde ocorre.** Em `mask_pii_in_record()` no
[`discovery_spike.py`](../fase-b-spike/ferramenta/discovery_spike.py), e nos artefatos em
`fase-b-spike/achados/execucoes/`. Campos observados:

| Endpoint | Campos expostos |
|---|---|
| `condominios` | `st_email_cond`, `st_telefone_cond`, `st_endereco_cond`, `st_cep_cond` |
| `unidades` | `cpf_proprietario`, `rg_proprietario`, `email_proprietario`, `telefone_proprietario` |
| `fornecedores` / `despesas` | e-mail, telefone, endereço, dados bancários |

**O que trava.** Viola **RI-002** ("PII minimizada em toda saída persistida") e toca **H8**
(LGPD). Hoje contido por `.gitignore` na pasta de execuções — contenção, não correção. Na Fase C,
ingerir 109 campos quando precisamos de 4 é problema de **minimização de dados** (LGPD art. 6º,
III), independente da questão de credenciais.

**Como resolver.**

1. **No spike:** estender o mascaramento por **nome de campo** — `email`, `telefone`, `celular`,
   `endereco`, `cep`, `rg`, `nascimento` — como já é feito para credenciais. *(Pendente.)*
2. **Na Fase C:** mesmo allowlist do [R-01](#r-01) resolve os dois de uma vez.
3. Manter os artefatos crus fora do git. *(Feito.)*

---

### R-03 — Permissão parcial filtra a carteira em silêncio {#r-03}

🔴 **Crítica** · Origem: **Fornecedor**

**O que é.** O token herda as permissões do usuário que o criou. Se esse usuário não enxerga
toda a carteira, **a API filtra sem erro e sem aviso** — a resposta parece completa.

**Onde ocorre.** Em qualquer listagem. Estruturalmente indetectável pelo cliente.

**O que trava.** É o risco mais perigoso do conjunto, porque **não tem sintoma**. Um índice
incompleto infla `sem_match_no_cadastro`, e a conclusão vira "a regra de associação não funciona"
quando o problema era permissão. Decisão de arquitetura tomada sobre medição corrompida.

**Como resolver.**

1. **Conferência externa obrigatória:** comparar `index_size` com a contagem real de condomínios,
   obtida **fora da API** (tela do ERP, confirmação da administradora). Nenhuma métrica da Fase 4
   vale antes disso.
2. Criar o token com usuário de visibilidade total, e **documentar quem o criou**.
3. Na Fase C, alertar quando o tamanho da carteira sincronizada mudar bruscamente entre execuções.

---

## B. Correção silenciosa dos dados

### R-04 — `DD/MM` × `MM/DD` indistinguível na leitura {#r-04}

🔴 **Crítica** · Origem: **Fornecedor**

**O que é.** Só o formato com barra aparece nas respostas (ex.: `08/10/2020`), zero ISO. Ler
`08/10` **não diz** se é 8 de outubro ou 10 de agosto. O estudo da Fase A registra `MM/DD/AAAA`
como `[DOC]` no *envio*, mas o formato de *resposta* não está confirmado.

**Onde ocorre.** Todos os campos `dt_*`. Incluindo **`dt_vencimento_pdes`** e `dt_despesa_des`.

**O que trava.** É o bug clássico de integração, e aqui incide sobre **data de vencimento de
despesa**. Errar o mês em documento financeiro produz pagamento fora do prazo, juros, ou
conciliação impossível — tudo sem erro em log.

**Como resolver.**

1. **Teste ativo com registro conhecido:** pegar uma despesa cuja data seja sabida (dia > 12,
   que desambigua sozinho) e comparar com a resposta. Barato e definitivo.
2. Conferência cruzada por inspeção do tráfego do ERP.
3. Até resolver, **nenhuma data lida da API pode ser gravada como data** — só como string bruta,
   com o formato marcado como indeterminado.

---

### R-05 — Nomes de campo vêm de heurística {#r-05}

🟠 **Alta** · Origem: **Método**

**O que é.** `st_cpf_cond` (CNPJ) e `id_condominio_cond` (identificador) foram **descobertos por
heurística**, não por documentação. O estudo da Fase A chutava `ST_CGC_CON` — errado.

**Onde ocorre.** `guess_cnpj_field()` e `guess_id_field()` no spike.

**O que trava.** Um nome errado **corrompe o índice da Fase 4 em silêncio**. Já aconteceu nesta
sessão: a heurística de id elegeu `id_planoconta_plc` (uma FK) em vez de `id_condominio_cond`.
Com esse id, o CNPJ casaria e toda comparação com o gabarito sairia errada — sem sintoma. A
heurística foi corrigida para pontuar por entidade, mas **continua sendo heurística**.

**Como resolver.**

1. **Confirmar por inspeção do tráfego do ERP** — a interface usa a mesma API; a aba *Network*
   revela os nomes exatos. É a conferência cruzada recomendada desde o plano da Fase B.
2. Uma vez confirmados, **fixar** via `SL_FIELD_CNPJ` / `SL_FIELD_ID` em vez de redescobrir.
3. Na Fase C, os nomes viram constantes explícitas — nunca heurística em produção.

---

### R-06 — Gabarito circular invalida a medição {#r-06}

🟠 **Alta** · Origem: **Método**

**O que é.** O `condominio_esperado_id` da amostra é a *verdade* contra a qual a regra é julgada.
Se ele for obtido **casando CNPJ**, a resposta é produzida pela mesma régua sob avaliação — a
precisão dá ~100% e não significa nada.

**Onde ocorre.** Na montagem da amostra rotulada (Fase 4). Não é código: é procedimento.

**O que trava.** Um go/no-go falsamente positivo é **pior que nenhum**: autoriza construir a
integração sobre uma chave nunca testada de verdade.

**Como resolver.**

1. Gabarito **sempre** de fonte independente: `id_condominio_cond` do registro de
   [`despesas`](../endpoints/despesas.md), atribuído por uma pessoa ao lançar.
2. **O `cnpj_papel_condominio` sai do PDF, via DocuParse.** Tirá-lo dos campos estruturados da
   despesa testaria o ERP contra o ERP. Regra prática: **da API pode vir tudo, menos esse campo**.
3. Documentar a procedência de cada linha da amostra, para auditar depois.

---

## C. Arquitetura da Fase C

### R-07 — Filtro server-side por CNPJ indefinido {#r-07}

🟠 **Alta** · Origem: **Ambiente**

**O que é.** Não se sabe se `condor/condominios` aceita filtro por CNPJ. Os 6 parâmetros
candidatos não estreitaram o resultado — mas com **1 condomínio** estreitar é impossível por
construção, então a sonda é **inconclusiva**, não negativa.

**Onde ocorre.** Fase 2 do spike, seção §7.2 do relatório.

**O que trava.** **A maior decisão de arquitetura da Fase C.** Sem filtro server-side, a
sincronização local da carteira vira **obrigatória** — e com ela vêm frescor, webhooks, e os
riscos [R-01](#r-01) e [R-02](#r-02), que só existem porque passamos a persistir dados do ERP.

**Como resolver.** Repetir a sonda contra carteira de **2+ condomínios** ([R-10](#r-10)). A
ferramenta já se declara não conclusiva sozinha nesse cenário.

---

### R-08 — `500` não é sinal de retry {#r-08}

🟠 **Alta** · Origem: **Fornecedor**

**O que é.** O modelo de erro é **híbrido, em duas camadas**: o gateway Sensedia responde `401`
em texto puro; o backend responde `403`/`404`/`500` com JSON `msg`. **O status HTTP diz que
falhou; o corpo diz por quê.**

**Onde ocorre.** Toda a API. Documentado no §7.4 do relatório.

**O que trava.** A camada de auth/retry da Fase C. Um cliente convencional trata `5xx` como
transitório e faz backoff — aqui, um `500` pode ser **permissão negada**, contra a qual retry
nenhum resolve. Resultado: loop infinito consumindo rate limit.

**Como resolver.** A camada de transporte **deve ler `msg` do corpo** e classificar em: falha
transitória (retryable), recusa de credencial (não retryable, alerta), erro de chamada (não
retryable, bug nosso). Nunca decidir retry só pelo status.

---

### R-09 — Rate limit desconhecido e sem cabeçalhos {#r-09}

🟠 **Alta** · Origem: **Fornecedor**

**O que é.** Rajada de 8 requisições: 8× `200`, nenhum `429`, **nenhum cabeçalho de limite**
exposto. O limite real não é público.

**Onde ocorre.** Toda a API.

**O que trava.** Se o [R-07](#r-07) resolver por sincronização local, a carteira inteira precisa
ser percorrida periodicamente — justamente o padrão que esbarra em rate limit. Sem cabeçalhos,
não há como adaptar dinamicamente.

**Como resolver.**

1. **Perguntar ao Superlógica** qual é o limite. É a via barata.
2. Até lá, **throttle conservador por padrão**, configurável.
3. Tratar `429` como cidadão de primeira classe desde o início — backoff exponencial com jitter.

---

### R-10 — Carteira de 1 condomínio {#r-10}

🟠 **Alta** · Origem: **Ambiente**

**O que é.** A credencial dá acesso a **1 condomínio** (`id_condominio_cond=7`), confirmado com
quem a forneceu.

**O que trava.** Três conclusões de uma vez:

| Bloqueado | Por quê |
|---|---|
| **Go/no-go da regra** | Sem outro condomínio, a *associação errada* não pode se manifestar. Um `% ERRADO` de zero seria artefato do ambiente |
| **Filtro server-side** ([R-07](#r-07)) | Filtrar não tem como estreitar 1 registro |
| **Paginação** | "Respeitou o limite" é trivialmente verdadeiro com baseline de 1 |

**Não trava** cobertura, `% sem CNPJ` e `% CNPJ inválido` — que medem a **qualidade de extração
do DocuParse** e podem rodar como ensaio já.

**Como resolver.** Acesso a ambiente com a carteira real. Único item sem contorno técnico. A
ferramenta já **retém o go/no-go** automaticamente quando o índice tem menos de 2 (FR-057).

---

## D. Lacunas de conhecimento

### R-11 — Expiração de credencial não observável {#r-11}

🟡 **Média** · Origem: **Fornecedor**

**O que é.** Tokens vão no header a cada requisição (stateless), mas **se e quando expiram** não
é verificável numa execução única. O campo `dt_expiracaoaccesstoken_usu` existe no schema —
sugere que expiram.

**O que trava.** A estratégia de renovação da Fase C. Descobrir em produção significa integração
parando sem aviso.

**Como resolver.** Perguntar ao Superlógica; observar ao longo do tempo; projetar a camada de
auth **assumindo que expiram**, com renovação e alerta. Investigar o papel do **Secret** (não
entra em nenhum dos dois headers — provavelmente serve à renovação).

---

### R-12 — `notafiscal` vaza erro de SQL {#r-12}

🟡 **Média** · Origem: **Fornecedor**

**O que é.** `GET condor/notafiscal` responde `500` com
`SQLSTATE[42S02]: Base table or view not found` — erro de banco vazando para o cliente.

**O que trava.** Nada hoje. Mas: (a) é divulgação de informação interna, e (b) indica endpoint
quebrado ou não provisionado — não "inexistente".

**Como resolver.** Reportar ao Superlógica. Confirmar se o módulo está provisionado para esta
licença antes de assumir que a entidade não existe.

---

### R-13 — Caminho de escrita totalmente desconhecido {#r-13}

🟡 **Média** · Origem: **Escopo** (deliberado)

**O que é.** O spike é read-only por construção (RI-001). **Nada** se sabe sobre `POST`/`PUT`:
se a despesa aceita anexo, em que formato, se há idempotência, como o erro chega na escrita.

**O que trava.** **H1** — se o objetivo final incluir *lançar despesa*, toda essa metade está
por descobrir. Também [R-14 do lote](#r-14) e a confirmação de anexo.

**Como resolver.** Passo separado e **explicitamente autorizado**, fora da Fase B. Nunca contra
produção sem sandbox. Escrever em sistema financeiro exige human-in-the-loop, idempotência e
rollback — todos ainda não desenhados.

---

### R-14 — CNPJ alfanumérico não suportado {#r-14}

🟡 **Média** · Origem: **Nossa**

**O que é.** A normalização e a validação de dígito verificador são **numéricas**. O rollout
brasileiro de CNPJ alfanumérico está em andamento.

**Onde ocorre.** `normalize_cnpj()` / `is_valid_cnpj()` no spike — e no futuro, na Fase C.

**O que trava.** Nada hoje. Quando aparecer um CNPJ alfanumérico no cadastro, ele será
classificado como **ausente ou inválido** — o documento cai em `cnpj_invalido` e a associação
falha silenciosamente.

**Como resolver.** Adaptar normalização e validação ao novo formato antes que ele apareça em
produção. Baixo custo agora, retrabalho depois.

---

## Resumo acionável

**Antes de escrever qualquer linha da Fase C:**

- Definir o **allowlist de ingestão** ([R-01](#r-01), [R-02](#r-02))
- Confirmar o **tamanho real da carteira** por fonte externa ([R-03](#r-03))
- Resolver a **ambiguidade de data** com teste ativo ([R-04](#r-04))
- Confirmar os **nomes de campo** por inspeção do tráfego ([R-05](#r-05))

**Antes de confiar em qualquer métrica da Fase 4:**

- Garantir a **independência do gabarito** ([R-06](#r-06))
- Ter carteira com **2+ condomínios** ([R-10](#r-10))

**Pedidos ao Superlógica** (agrupáveis num contato só):

- Exposição de campos `_usu` na listagem ([R-01](#r-01))
- Qual é o **rate limit** ([R-09](#r-09))
- **Expiração** de token e papel do Secret ([R-11](#r-11))
- `notafiscal` retornando erro de SQL ([R-12](#r-12))
