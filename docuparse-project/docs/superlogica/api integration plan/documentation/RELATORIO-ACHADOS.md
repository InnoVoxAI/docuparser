# RELATÓRIO DE ACHADOS — spike de descoberta (Fase B)

**Status: Fases 0–3 EXECUTADAS. Fase 4 (regra de associação) NÃO EXECUTADA.**

_Execução: 2026-08-07 19:15 · `base_url` `https://api.superlogica.net/v2` · modo: **completo** ·
artefatos em `achados_out/`._

> Este arquivo é o que **persiste** depois do descarte do `discovery_spike.py`.
> Todo dado abaixo foi **produzido pela ferramenta** e sai dos artefatos daquela execução
> (`achados.json` / `achados.csv`) — não de observação manual de terminal.
>
> ⚠️ **Ressalva que atravessa o relatório inteiro:** a credencial enxerga **1 condomínio**
> (`id_condominio_cond=7`, "COND. EDF. BETULA"). Não é possível distinguir daqui se a carteira
> tem mesmo 1 ou se a credencial só vê 1 — é o edge case de *permissão parcial* previsto na
> spec. Toda conclusão que dependa de **volume** está marcada como não conclusiva.

---

## §7.4 — Autenticação e modelo de erro ✅ **RESOLVIDO**

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

### Mapeamento das credenciais (confirmado por sondagem)

| Header | Recebe |
|---|---|
| `app_token` | **App token** |
| `access_token` | **Access token** |

O **Secret** não entra em nenhum dos dois — é rejeitado nas duas posições (401 do gateway).
Serve a outro fluxo. O spike não o consome.

---

## §7.1 / §7.8 — Endpoints e campos ✅ **RESOLVIDO**

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

### Envelope das respostas

As entidades vêm **duplamente aninhadas**: `[ { "condominio": [ {…109 campos…} ] } ]`. Sem
desembrulhar, o achado reportaria 1 registro com um único "campo" chamado `condominio`.

### Nomes de campo descobertos (§7.2-campo)

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

## §7.2-filtro / §7.5 / §7.6 / §7.7 — Mecânica ⚠️ **PARCIAL**

### Filtro server-side por CNPJ — ⛔ **NÃO CONCLUSIVO**

Os 6 parâmetros candidatos (`CNPJ`, `cnpj`, `pesquisa`, `busca`, `ST_CGC_CON`, `ST_CNPJ_CON`)
foram testados com um CNPJ real da carteira. Nenhum estreitou o resultado — **mas com 1
condomínio visível, estreitar é impossível por construção**: com ou sem filtro, o resultado é
o mesmo registro.

**A bifurcação de arquitetura mais cara da Fase C segue indecidida:**

> Se não existir filtro server-side por CNPJ, **a sincronização local da carteira passa a ser
> obrigatória** e frescor/webhook deixa de ser opcional.

Para decidir, repetir contra uma carteira com **2 ou mais** condomínios. (Uma versão anterior
deste relatório concluía "SEM filtro" — era falsa confiança, corrigida na ferramenta.)

### Paginação — ⚠️ não conclusivo

`itensPorPagina`, `limit` e `porPagina` foram aceitos, mas com baseline de 1 registro
"respeitou o limite" é trivialmente verdadeiro e **não prova** que a paginação funciona.
Também depende de carteira maior.

### Formato de data — ✅ observado

Só o formato **com barra** aparece nas respostas (ex.: `08/10/2020`); zero ocorrências de ISO.
**A leitura não distingue `DD/MM` de `MM/DD`** — o teste ativo depende de existir filtro de
data. Continua em aberto, e é o bug clássico da integração.

### Rate limit — ✅ sem sinal de limite

Burst de 8 requisições: **8 × HTTP 200**, nenhum `429`, **nenhum cabeçalho de rate limit**
exposto. O limite real não é público. **Throttle conservador na integração.**

### Lote — ⬜ deferido

O padrão `params[]` da v1 era `POST`. Confirmação depende do caminho de escrita, fora do
escopo read-only.

---

## §7.3 — Anexos na leitura ✅ **RESOLVIDO (parcialmente)**

2 despesas amostradas. Campos candidatos a anexo:

| Campo | Formato aparente |
|---|---|
| `arquivos` | conteúdo com 1177 caracteres — **o candidato forte** |
| `documentos_pendentes` | 2 caracteres |
| `st_documento_des`, `st_serienota_des` | vazios |

**Há campo de anexo na leitura.** O formato exato (URL / base64 / id) ainda não foi
classificado — `arquivos` precisa de inspeção do conteúdo.

**Confirmar se a despesa aceita anexo na ESCRITA só se resolve escrevendo** → passo autorizado
à parte, fora do spike (H1).

---

## ⭐ §5 / §7 ⭐ — Regra de associação ⬜ **NÃO EXECUTADA**

Não rodou por **falta de amostra rotulada**. O bloqueio técnico caiu — `st_cpf_cond` e
`id_condominio_cond` estão identificados, então a Fase 4 tem como montar o índice.

**Nenhum go/no-go foi emitido.** Nenhuma métrica de cobertura, precisão ou % de associações
erradas existe. A regra documento↔condomínio permanece **hipótese não testada**.

E há um problema de fundo, independente da amostra:

> **Com 1 condomínio na carteira, a Fase 4 não produz um go/no-go significativo.** Um índice de
> uma entrada só permite "casou" ou "não casou"; a **associação errada** — o número de risco
> financeiro/jurídico, o motivo de a Fase 4 existir — não tem como se manifestar. Confundir
> um condomínio com outro exige que haja outro.

**A Fase 4 precisa de um ambiente com a carteira real.** Confirmar com quem forneceu os tokens
se esta licença é sandbox de demonstração ou produção com visibilidade restrita.

---

## Correções feitas na ferramenta

A execução expôs sete defeitos, todos corrigidos e cobertos por auto-verificação
(**13 → 26 checagens** offline):

| # | Defeito | Impacto se não corrigido |
|---|---|---|
| 1 | `autenticou` era `status != 401` | Reportava autenticação OK sob erro de permissão |
| 2 | Erro no corpo só era buscado em `status` (v1) | O `msg` da v2 passava despercebido |
| 3 | Envelope de erro contava como registro | `msg` viraria "campo" da entidade |
| 4 | `probe()` não mandava parâmetro obrigatório | **Todos os controllers dariam falso "não existe"** |
| 5 | `extract_records` não desembrulhava o aninhamento | Nenhum campo seria descoberto, com dados válidos na mão |
| 6 | `mask_pii_in_record` só mascarava CPF/CNPJ | **Gravaria tokens e senhas em disco** (RI-002/RI-004) |
| 7 | `guess_id_field` escolhia por contagem | Elegeu `id_planoconta_plc`; o índice da Fase 4 mapearia CNPJ → id errado, **corrompendo o go/no-go em silêncio** |

Mais dois ajustes de honestidade: a conclusão do filtro e a da paginação agora se declaram
**não conclusivas** quando a carteira é pequena demais para sustentá-las, e a sonda de rate
limit passou a mandar o parâmetro obrigatório (antes media 8 × 403, não 8 × 200).

Fora da ferramenta: [`run_script.sh`](../../../../run_script.sh) tinha o caminho `/docuparser`
do dev container hardcoded e não carregava o `.env` num clone no host.

---

## Encaminhamento

**Bloqueadores da Fase 4, em ordem:**

1. **Ambiente com a carteira real** (2+ condomínios). Destrava o go/no-go **e** a bifurcação do
   filtro e a paginação. É o item de maior alcance.
2. **Amostra rotulada.** O gabarito (`condominio_esperado_id`) **não pode** ser obtido casando o
   CNPJ — seria usar a resposta para corrigir a própria prova. Tem que vir de fonte
   independente: o arquivamento manual já correto no ERP, ou a pasta de origem do documento.
3. **H7** — mapa tipo de documento → qual campo é o papel-condomínio.

**Descoberta manual pendente (não depende de credencial):** os 4 controllers `404`
(`condominos`, `contatosunidade`, `cobrancas`, `planodecontas`) e o formato do campo `arquivos`
das despesas, ambos resolvíveis por inspeção do tráfego do ERP.

**Nada foi escrito no ERP.** Todas as requisições foram `GET`, garantido pela guarda do cliente
HTTP (RI-001).
