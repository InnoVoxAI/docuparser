# Pontos a esclarecer — validação humana

> **O que é este arquivo:** registro persistente das decisões de **produto/negócio** que precisam de **validação humana** (PO, cliente, arquitetura, jurídico) para o projeto de integração DocuParse × API Condomínios (Superlógica). É o complemento do trilho *humano* da §8 do documento de Fase A.
>
> **O que NÃO está aqui:** perguntas que só a API responde (paths, campos, formato de erro, paginação, existência de filtro/anexo). Essas ficam no **trilho técnico** e são resolvidas na etapa de validação pré-execução da **Fase B** — ver §7 da Fase A.
>
> **Como usar:** manter vivo entre as fases. Cada item vira, quando resolvido, um fato que alimenta o `Specify` real da integração (Fase C). Atualizar a coluna *Resolução* conforme as respostas chegam.

| Campo | Significado |
|---|---|
| **Bloqueia Fase B?** | Se a resposta é necessária *antes* de escrever/rodar o spike da Fase B |
| **Suposição atual** | O default assumido enquanto não há resposta (para não travar o avanço) |

---

## H1 — Objetivo final: identificar/arquivar × lançar despesa

**Pergunta:** o fim é apenas **identificar e arquivar** o documento (vincular ao condomínio, guardar), ou também **lançar a despesa** no ERP via API?

**Por que importa:** define o projeto como *read-only* (consulta + reconciliação) ou *bidirecional* (escrita). Muda toda a Fase C e o nível de cuidado (escrever em sistema financeiro exige human-in-the-loop, idempotência, rollback).

**Resolução:** PO / cliente.
**Bloqueia Fase B?** Não — o spike pode explorar os *dois* caminhos, sempre em **dry-run** no lado de escrita.
**Suposição atual:** a definir. Assumir "identificar/arquivar + montar (sem enviar) o payload de despesa" até haver decisão.

---

## H2 — Fonte da verdade / dono da escrita

**Pergunta:** o DocuParse **empurra** dados para o Superlógica, ou o Superlógica é o **dono** dos dados e o DocuParse apenas **vincula/anota** do lado dele?

**Por que importa:** decide read-only × bidirecional e onde vive o estado autoritativo.

**Resolução:** PO / arquitetura.
**Bloqueia Fase B?** Não.
**Suposição atual:** **provavelmente o Superlógica é a fonte da verdade** (indicado pela equipe). A confirmar.

---

## H3 — Multi-tenancy no nível *administradora*

**Pergunta:** o DocuParse atende **uma** administradora (um Superlógica, um par `app_token`/`access_token`) ou **várias** administradoras, cada uma com sua conta e seus próprios tokens?

**Esclarecimento do eixo:** já está confirmado **[PROD]** que o DocuParse é multi-tenant no nível de **condomínio** (vários condomínios, cada um com seus documentos) — mas isso vive dentro de *uma* administradora. Esta pergunta é o nível acima: **quantas administradoras/tokens** o sistema orquestra.

**Por que importa:** muda arquitetura de credenciais (um token × cofre de N tokens), isolamento entre clientes e o design geral da sincronização.

**Resolução:** PO.
**Bloqueia Fase B?** **Parcial** — o spike roda com *um* token, mas o desenho geral depende da resposta.
**Suposição atual:** assumir **1 administradora / 1 token** para o spike; confirmar escala antes da Fase C.

---

## H4 — Volume da carteira

**Pergunta:** quantos condomínios a carteira tem (ordem de grandeza)?

**Por que importa:** define se "sincronizar a lista inteira de condomínios localmente" é trivial ou se **paginação + rate limit** viram o problema central (conecta com §7, itens 2 e 5).

**Resolução:** cliente / PO.
**Bloqueia Fase B?** Não.
**Suposição atual:** ordem de **dezenas a centenas** até confirmar.

---

## H5 — Tolerância a erro de associação (política)

**Pergunta:** qual nível de confiança **auto-confirma** a associação documento↔condomínio, e a partir de qual vai para **revisão humana**?

**Por que importa:** é uma **restrição de design** do matching e do fluxo de exceção. **Associar ao condomínio errado num sistema financeiro tem impacto financeiro e jurídico.**

**Distinção importante:** a *viabilidade técnica* da regra de match (CNPJ do papel-condomínio → condomínio) será **testada no spike** (Fase B, §7 item ⭐, e fluxo provisório §5). Este item aqui é a *política de tolerância* — decisão humana que só faz sentido depois de ver as taxas de acerto/erro medidas no spike.

**Resolução:** PO + análise de risco (informada pelos números do spike).
**Bloqueia Fase B?** Não — o spike **mede**; a política vem depois.
**Suposição atual:** nada auto-confirmado até o spike medir; tudo passa por revisão humana no início.

---

## H6 — Idempotência / duplicidade

**Pergunta:** como evitar lançar **duas vezes** o mesmo documento — inclusive uma despesa que já foi lançada **manualmente** no ERP por um operador?

**Por que importa:** integridade financeira. Reprocessamento e concorrência não podem gerar despesa duplicada.

**Resolução:** PO + design.
**Bloqueia Fase B?** Não (relevante para a Fase C, se H1 incluir escrita).
**Suposição atual:** a definir. Chave de idempotência provável = hash do documento + `id_condominio` + valor + vencimento; e, antes de lançar, consultar despesas existentes do condomínio para detectar duplicata.

---

## H7 — Taxonomia de tipos de documento + papel-CNPJ por tipo

**Pergunta:** qual o **conjunto completo** de tipos que o DocuParse processa (boleto, NF, conta de consumo, contrato, recibo, extrato bancário, apólice…?) e, **para cada tipo**, qual campo extraído é o papel-condomínio (ou se o tipo não tem um)?

**Por que importa:** define a **matriz de teste** do spike (incl. a seção ⭐ de validação da regra) e a lógica por tipo. Alguns tipos podem nem virar despesa, e alguns podem não ter CNPJ do condomínio (ex.: consumo em nome de terceiro — ver riscos no §5).

**Contexto:** já confirmado **[PROD]** que, quando há CNPJ, ele sai rotulado por papel (ex.: NF → `cnpj_tomador`/`cnpj_fornecedor`). Falta a **lista completa** e o mapa por tipo.

**Resolução:** equipe DocuParse.
**Bloqueia Fase B?** **Parcial** — o spike precisa de, no mínimo, a lista dos tipos que já saem com papel-CNPJ para montar a amostra de teste.
**Suposição atual:** começar por **NF** (papéis confirmados), **boleto** e **conta de consumo**; expandir depois.

---

## H8 — Transversais: LGPD e trilha de auditoria

**Pergunta:** (a) qual o tratamento adequado dos **dados pessoais** (CPF/CNPJ, dados de morador) puxados do Superlógica para a base do DocuParse — retenção, minimização, base legal? (b) Que **trilha de auditoria** a decisão de associação precisa registrar (o quê casou com o quê, quando, por qual chave, auto ou manual)?

**Por que importa:** conformidade (LGPD) e rastreabilidade — num contexto financeiro, provavelmente exigidas.

**Resolução:** jurídico / PO.
**Bloqueia Fase B?** Não.
**Suposição atual:** registrar a trilha de associação desde já; minimizar retenção de dados pessoais no spike (usar amostra reduzida/anonimizada quando possível).

---

### Prioridade sugerida
Responder **antes de escrever a Fase B**: **H3** (arquitetura de credenciais) e **H7** (matriz de teste). Os demais podem seguir como suposição registrada e ser respondidos em paralelo ou pelo próprio spike.
