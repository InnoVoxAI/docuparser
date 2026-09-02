---
title: Redesign — Visão Geral de Processos (nova página inicial)
type: note
permalink: features/redesign-process-overview
tags: [frontend, backend, processes, redesign, ux]
---

# Redesign — Visão Geral de Processos

Redesenho para reduzir carga cognitiva: a antiga tela `/processes`
(sidebar de lista + diagrama de steps técnicos) foi substituída por uma
**tabela de processos que é a página inicial (`/`) do app**.

## Decisões

- **`/` = Visão Geral de Processos** para quem tem `inbox.view` OU
  `operations.access` (`app/router.tsx` → `IndexRoute`). Quem não tem nenhuma
  das duas cai na 1ª tela permitida (comportamento antigo do `IndexRedirect`).
- **Sem sidebar em `/`**: `AppLayout` detecta `pathname === '/'` e renderiza
  **nenhum cabeçalho** — só o conteúdo + `app/OverviewMenu.tsx`, um botão "≡"
  flutuante (`fixed` canto sup. dir.) que abre um dropdown com abas
  Processos/Estatísticas, links pras demais telas (`NAV_ITEMS` + `PermissionGuard`)
  e Sair. (`OverviewTopBar` foi removido — 2ª iteração de "menos chrome".)
  As demais rotas seguem com o layout antigo (`AppSidebar`/`AppHeader`/`MobileNav`).
  Nota: o menu é sempre montado (só `hidden` quando fechado) pra os testes de
  `permissions/auth/screens` continuarem achando os rótulos de nav.
- **`/processes` → redirect para `/`** (mantido só p/ links antigos). Item
  "Processos" saiu de `NAV_ITEMS`.
- **Status "de negócio"** (4 rótulos, para analistas, não devs), calculados no
  backend em `documents/services/process_dashboard.py`
  (`business_status_group` / `business_status_label`) e expostos como
  `status_label` no `ProcessSummarySerializer`:
  - `has_error` → **Erro**
  - `VALIDATION_PENDING` → **Aguardando validação**
  - `APPROVED` / `ERP_*` → **Aguardando classificação**
  - resto (`RECEIVED`, OCR/extração em curso, `REJECTED`) → **Em Fila**
  - Não existe "Concluído": classificação acontece depois da validação e
    segue **fora da plataforma**.
- **Filtro** `?status_group=` em `GET /processes` (aceita CSV; o front manda
  um valor só) — **dropdown** ("Todos" + os 4 status) no topo da tabela.
  Ao lado, **busca por nome do arquivo** (`?search=`, já suportado por
  `_apply_search`) e o botão "Novo processo". Convive com `filter`/`stage`.
- **Breakdown da linha expandida** (`ProcessBreakdown`): 4 caixas
  `Em fila → Ingestão → Validação → Classificação`, derivadas dos steps de
  `GET /documents/{id}/pipeline`. **Fallback importante** (`_STEPS_DONE_BY_STATUS`
  em `build_pipeline_detail`): quando um step não tem `TaskExecution`, o
  `document.status` diz até onde o processo avançou (ex.: `VALIDATION_PENDING`
  ⇒ ocr/extraction = OK). Sem isso, um processo "Aguardando validação"
  aparecia com "Em fila / Ingestão" ainda pendentes — bug reportado.
  Só duas caixas são interativas:
  - **Ingestão** clicável **apenas em erro** → `IngestionLogsModal` (logs das
    execuções de ocr/extraction).
  - **Validação** clicável **apenas aguardando decisão** → `ValidationDrawer`
    (full-height à direita) que **reaproveita `ValidationView` inteira** com
    `stacked` (arquivo em cima, campos embaixo — o grid `xl:` original abria
    lado a lado e apertado no drawer). Ambos os popups usam o hook
    `shared/hooks/useBodyScrollLock` pra travar o scroll do fundo.
  - Backend ganhou um step estático `classification` em `build_pipeline_detail`
    (como `register`). **Nunca fica "OK/Concluído"** (a classificação corre
    fora da plataforma): só `PENDING` ou, em `ERP_FAILED`, `ERROR`. O front
    deriva "em andamento" quando `validation == OK`. (Bug reportado: caixa
    "Concluído" num processo "Aguardando classificação".)
- **Permissão**: `processes_dashboard_view` / `document_pipeline_view` /
  `process_stats_view` usam `require_any_permission("inbox.view",
  "operations.access")` (novo factory em `users/permissions.py`) — a Visão
  Geral é a home de qualquer operador.

## Tela de Estatísticas (`/stats`)

Página agregada, também **chromeless** (`AppLayout.isOverview` cobre `/` e
`/stats`; `OverviewMenu` flutuante troca de seção).

- **`GET /processes/stats`** (`build_process_stats` em `process_dashboard.py`):
  `{ total, by_status (4 grupos), by_stage (register/ocr/extraction/
  validation_decision/classification), errors {documents_with_error, by_step,
  by_type}, validation {approved, rejected}, volume {last_24h/7d/30d},
  avg_duration_ms (por etapa, só execuções OK), manual_retries }`. Agregação
  Python/ORM sobre toda a base — ok pra POC.
- Front: `ProcessStatsView` + `StatBreakdown` (barras horizontais),
  `useProcessStatsQuery` (poll 20s), rota `ProcessStatsRoute` (`{ path: 'stats' }`
  em `ProcessesRoutes`, gate `inbox.view` OU `operations.access`).

## Dependência cruzada (aceita)

`modules/processes/components/ValidationDrawer.tsx` importa `ValidationView` de
`modules/documents` (barrel) e `useSchemasQuery` de `modules/settings` —
mesma exceção já documentada para `ValidationRoute` (ver
`ProcessesView`/`ValidationRoute` histórico). `AppLayout` ganhou
`selectDocument(id)` no outlet context (seleciona sem navegar) para o drawer
reusar o carregamento de `selectedDocument`.

## Ambiente de teste (atenção)

`flows.test.tsx` / `pagination.test.tsx` / `screens.test.tsx` (teste 2) já
falhavam em `dev` **antes deste redesign** por um bug de ambiente local
(`TypeError: RequestInit: Expected signal to be an instance of AbortSignal` —
undici + `@mswjs/interceptors` + `createBrowserRouter`). O redesign não
regride nada: `permissions`/`auth`/testes de componente passam; contagem de
falhas idêntica à baseline (16). Rodar em CI/container para o verde real.

## Arquivos principais

- Front: `modules/processes/` reescrito — `ProcessOverviewView`, `ProcessTable`,
  `ProcessRowDetail`, `ProcessBreakdown`, `ProcessFilters` (dropdown),
  `ProcessStatusBadge`, `IngestionLogsModal`, `ValidationDrawer`,
  `ProcessStatsView`, `StatBreakdown`. `app/OverviewMenu.tsx` (menu flutuante).
  Removidos `ProcessesView`/`ProcessesSidebar`/`ProcessPipelineDiagram`/
  `StepDetailPanel`/`useRetryStepMutation` (retry manual saiu do escopo),
  `app/OverviewTopBar.tsx`.
- Back: `documents/services/process_dashboard.py`, `documents/serializers.py`,
  `documents/views.py`, `users/permissions.py`,
  `documents/tests/test_process_dashboard_api.py`.
