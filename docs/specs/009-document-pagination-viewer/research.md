# Phase 0 — Research: Paginação e Visualização de Documentos

Decisões técnicas, com base no estado atual do código
(`backend-core/documents/` e `frontend/src/main.tsx`).

## D1 — Estratégia de paginação no backend

**Decisão**: Paginação **manual por query params** no `documents_inbox_view`,
retornando um envelope `{ results, count, page, page_size, total_pages }`.
Parâmetros: `page` (default 1), `page_size` (default 25, **cap 25**), além dos
filtros já existentes `status`/`tenant` e do novo `search`. Reusar o helper
`_positive_int` já presente em `documents/views.py`. Aplicar o recorte com
`queryset[offset:offset+page_size]` e `count = queryset.count()` antes do slice.

**Rationale**:
- DRF **não** tem paginação default configurada (`REST_FRAMEWORK` só define auth)
  e as views são `@api_view` retornando `Response(list)` — paginação automática
  do DRF não se aplica sem reescrever para classes paginadas.
- O projeto já usa paginação/limite manual por query param em
  `dlq_events_view`/`_positive_int`, e a feature 007 já retorna
  `{results, count, ...}` — manter esse padrão é o caminho de menor atrito e
  mais consistente internamente.
- `count()` + slice no banco evita o `[:200]` atual e o carregamento amplo.

**Alternativas consideradas**:
- `PageNumberPagination`/`LimitOffsetPagination` do DRF: exigiria converter as
  FBVs em GenericAPIView/ViewSet — refator maior, sem ganho proporcional.
- Envelope `{data, error, meta}` da Constituição III: ver D7.

## D2 — Busca e filtros server-side

**Decisão**: Mover a busca para o backend via parâmetro `search`, aplicando
`icontains` sobre `original_filename`, `status`, `document_type` e `channel`
(com `Q(...) | Q(...)`). Mapear termos de status amigáveis comuns (ex.: "aprovado"
→ `APPROVED`, "rejeitado" → `REJECTED`, "pendente" → demais) para preservar a
experiência atual de busca por rótulo. Filtros por `status` (single ou conjunto)
continuam por query param.

**Rationale**: FR-005/FR-007 exigem busca correta sobre **todo** o conjunto e
proibem carregar a base inteira no cliente. O `filterDocuments` atual roda no
front sobre o array completo — incompatível com paginação.

**Busca por valor de campo extraído (Clarifications 2026-06-24 — MANTER)**: além
de nome/status/tipo/canal, a busca server-side também pesquisa dentro de
`extraction_result.fields`, preservando o comportamento atual. Como `fields` é um
JSONField, a implementação aplica busca textual sobre o JSON — opções a decidir no
/speckit-tasks: (a) `icontains` no JSON serializado (cast para texto), simples e
suficiente para a base atual; (b) operadores JSONB do PostgreSQL para busca mais
precisa. Mitigar o custo com: limitar a busca de campos ao termo já fornecido (só
quando há `search`), confiar na paginação para reduzir materialização, e medir o
p95 (< 200 ms, Constituição IV); se necessário, avaliar índice (ex.: GIN) como
melhoria incremental.

## D3 — Filtros por tela (status buckets) e múltiplos status

**Decisão**: Suportar `status` aceitando **lista** (ex.: `?status=RECEIVED,OCR_COMPLETED,...`)
para os "buckets" das telas:
- **Inbox/pendentes**: `RECEIVED, OCR_COMPLETED, EXTRACTION_COMPLETED, VALIDATION_PENDING`.
- **Aprovados**: `APPROVED`.
- **Rejeitados**: `REJECTED`.
- **Dashboard ("Documentos")**: sem filtro de status (todos), paginado.

**Rationale**: Hoje o frontend deriva esses buckets do array único via `useMemo`.
Com paginação por tela, o filtro precisa ir ao backend. Reusa o filtro `status`
já existente, estendido para CSV.

## D4 — Métricas do Dashboard (totais por bucket)

**Decisão**: As métricas (Total, Pendentes, Aprovados, Falhas) **não** podem mais
ser derivadas de um array completo. Obter as contagens via consultas de
`count()` por bucket. Opção adotada: reutilizar o `count` do envelope paginado —
o Dashboard dispara as consultas de contagem por bucket (page_size mínimo, lendo
apenas `count`) **ou** um endpoint leve de resumo. **Preferência**: derivar dos
`count` das próprias listas já carregadas quando possível; onde faltar, emitir
consultas de contagem dedicadas (`count()` por `status`), baratas e indexadas.

**Rationale**: Mantém as métricas corretas sem carregar todos os registros.
Evita criar um novo endpoint se as contagens já vierem dos envelopes.

**Alternativa**: novo endpoint `GET /documents/summary` retornando os 4 contadores
— considerar no /speckit-tasks se as contagens por envelope ficarem desajeitadas.

## D5 — Autorização do endpoint de arquivo (visualização)

**Decisão**: `document_file_view` passa a aceitar **dois** modos de auth:
(a) token interno de serviço (comportamento atual, para serviços) **e**
(b) **JWT do usuário** + `require_permission("inbox.view")` (igual à listagem),
quando a requisição vier autenticada como usuário. O frontend busca o arquivo via
`axios` com `responseType: 'blob'` (o interceptor já injeta o `Authorization`),
respeitando a permissão, e renderiza via `URL.createObjectURL` (sem download).

**Rationale**:
- Hoje o endpoint só valida o token interno; um `<iframe src>`/`<img src>` do
  navegador não envia o header JWT, então em produção (token interno definido) a
  pré-visualização falharia e/ou não respeitaria a permissão do **usuário**
  (FR-015).
- Buscar como blob autenticado carrega o JWT, satisfaz FR-015 e FR-011 (sem
  download) e funciona igualmente para armazenamento local ou externo (o endpoint
  abstrai o backing store).

**Alternativas consideradas**:
- URL assinada de curta duração: mais robusto para storage externo, porém
  introduz emissão/validação de assinatura — overkill para o escopo atual.
- Manter `<iframe src>` simples: não respeita permissão de usuário em produção.

## D6 — Pré-visualização inline no frontend (sem download)

**Decisão**: Reusar a técnica já presente na `ValidationView` (iframe para PDF,
`<img>` para imagens), mas alimentada por **object URL** de um blob autenticado
(D5). Adicionar a pré-visualização como **uma seção adicional ao lado** das
informações já exibidas no `EmailMetadataModal` (sem remover nada). Estados de
loading/erro explícitos; `URL.revokeObjectURL` no cleanup. Fallback amigável para
formatos sem preview nativo (sem forçar download).

**Rationale**: FR-012/FR-019 (acrescentar sem remover), FR-011 (sem download),
FR-013 (todos os formatos atuais: PDF + PNG/JPG/TIFF/WebP), boa UX.

## D7 — Forma do envelope vs. Constituição III

**Decisão**: Usar `{ results, count, page, page_size, total_pages }` (estende o
padrão da feature 007) em vez de `{ data, error, meta }`.

**Rationale/Trade-off**: registrado em `plan.md` → Complexity Tracking. Migrar
para o envelope canônico é um esforço transversal (todos os endpoints + cliente)
que deve ser uma feature própria; fazê-lo só aqui pioraria a consistência.

## D8 — Estado e navegação de paginação no frontend

**Decisão**: Introduzir um tipo `Paginated<T>` em `types.ts` e um pequeno
componente `Pagination` (controles: anterior/próxima, página atual/total, total
de registros) + estado por tela (`page`, `search`) com efeito que busca a página
quando `page`/`search`/bucket mudam. Alterar `search` reseta `page` para 1
(FR-006). A atualização automática (polling de processamento) refaz a busca da
**página atual** preservando filtros (FR-009).

**Rationale**: Componentização mínima e coesa (Code Quality), reutilizável entre
as telas, com cobertura de testes (Vitest).

## D9 — Compatibilidade de contrato e testes

**Decisão**: A mudança de `GET /documents` (lista crua → envelope paginado) é
**breaking** para o cliente, que controlamos. Atualizar os acessos `api.get` e os
handlers MSW. Adicionar testes de contrato/integração no backend (paginação,
busca, limites, auth de arquivo) **antes** da implementação (Constituição II).

**Rationale**: FR-018 (sem regressão) e política de testes do projeto.
