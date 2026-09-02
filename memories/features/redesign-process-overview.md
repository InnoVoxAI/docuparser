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
  `app/OverviewTopBar.tsx` (marca + navegação enxuta + Sair) no lugar de
  `AppSidebar`/`AppHeader`/`MobileNav`. As demais rotas seguem com o layout
  antigo intacto.
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
- **Filtro** `?status_group=` (CSV, multi-seleção) em `GET /processes` — chips
  no topo da tabela. Convive com os `filter`/`stage` antigos.
- **Breakdown da linha expandida** (`ProcessBreakdown`): 4 caixas
  `Em fila → Ingestão → Validação → Classificação`, derivadas dos steps de
  `GET /documents/{id}/pipeline`. Só duas são interativas:
  - **Ingestão** clicável **apenas em erro** → `IngestionLogsModal` (logs das
    execuções de ocr/extraction).
  - **Validação** clicável **apenas aguardando decisão** → `ValidationDrawer`
    (full-height à direita) que **reaproveita `ValidationView` inteira**.
  - Backend ganhou um step estático `classification` em `build_pipeline_detail`
    (como `register`), estado tirado de `document.status`.
- **Permissão**: `processes_dashboard_view` / `document_pipeline_view` passaram
  de `require_permission("operations.access")` para
  `require_any_permission("inbox.view", "operations.access")` (novo factory em
  `users/permissions.py`) — a Visão Geral é a home de qualquer operador.

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
  `ProcessRowDetail`, `ProcessBreakdown`, `ProcessFilters`,
  `ProcessStatusBadge`, `IngestionLogsModal`, `ValidationDrawer`. Removidos
  `ProcessesView`/`ProcessesSidebar`/`ProcessPipelineDiagram`/`StepDetailPanel`/
  `useRetryStepMutation` (retry manual saiu do escopo).
- Back: `documents/services/process_dashboard.py`, `documents/serializers.py`,
  `documents/views.py`, `users/permissions.py`,
  `documents/tests/test_process_dashboard_api.py`.
