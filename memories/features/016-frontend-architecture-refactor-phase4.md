---
title: 016 Frontend Architecture Refactor — Phase 4 (US2) progress
type: note
permalink: features/016-frontend-architecture-refactor-phase4
tags: [frontend, refactor, 016]
---

# 016 Frontend Architecture Refactor — Phase 4 (US2) progress

Written by an agent session that was interrupted mid-task ("vou continuar com
outro agente para evitar drift"). Full detail lives in
`docs/specs/016-frontend-architecture-refactor/tasks.md` (per-task `Resultado`
notes) — this note is a pointer + the non-obvious things worth remembering.

## State (updated 2026-07-24, after Phase 4g)

- Branch: `016-frontend-architecture-refactor`.
- Sub-phases done: **4a** (`86585ae`, shared UI primitives), **4b**
  (`8322754`, `modules/auth`), **4c** (`156ff46`, routing — T022-T025), **4d**
  (`42d9c9e`, `modules/documents` + TanStack Query — T026-T033), **4e**
  (`cba0358`, `modules/operations` + TanStack Query — T034-T035), **4f**
  (`9c55ef4`, `modules/settings` + RHF/Zod — T036-T040), **4g**
  (uncommitted at write time, `modules/admin` + TanStack Query — T041). All
  gates green (typecheck/lint/test/build) at each step.
- **4g** extracted `GerenciarUsuarios`/`GerenciarRoles` into `modules/admin`,
  converted the 5 manual axios calls (`/users` GET, `/roles` GET/POST/PATCH/
  DELETE, `/permissions` GET) to `useUsersQuery`/`useRolesQuery`/
  `usePermissionsQuery`/`useUserMutations`/`useRoleMutations` (TanStack Query
  v5, each mutation invalidating only its own list key — `adminKeys.users()`
  or `adminKeys.roles()`, not a shared `adminKeys.all`, since the original
  code never cross-refreshed the other list on mutation), split both
  180ish-line views into container + table + form-modal (mirrors the 4e
  `OperationsView` split), and wired `router.tsx` to consume `AdminRoutes`.
  `main.tsx` shrank from 1075 to 712 lines. **Deliberately did NOT fold
  `TenantsView` in** — see the resolved note under "4g-specific" below; this
  reverses the plan recorded in the old item 6 further down this file.
- **4d** extracted `Dashboard`/`InboxView`/`ApprovedView`/`RejectedView`/
  `ValidationView`/`DocumentTable`/`ExtractedFieldsModal`/
  `RejectedDocumentModal`/`LangExtractPanel`/`DocumentMetadataPanel`/
  `FieldVersionHistoryModal` into `modules/documents`, converted
  `useDocumentPage`→`useDocumentsQuery` + `fetchDocumentCount`→
  `useDocumentCount` + reprocess/delete/validate→`useDocumentMutations`
  (TanStack Query v5), and wired `router.tsx` to consume `DocumentsRoutes`
  instead of inline route components. `main.tsx` shrank from ~5456 to ~3600
  lines but **`useDocumentPage`/`PAGE_SIZE`/`EMPTY_PAGE` are intentionally
  still there** — `ReferenceDocumentPanel` (Configurações) still uses the old
  hook and isn't extracted until Phase 4f (T036-040). Don't delete them before
  then.
- **4e** extracted `OperationsView` (DLQ summary/events/requeue) into
  `modules/operations`, split the 220-line monolith view into a container
  (`OperationsView.tsx`) + 3 presentational components
  (`DlqStreamSummary`/`DlqEventsTable`/`DlqEventDetail`, all ≤150 lines),
  converted the 3 manual axios calls to `useDlqSummaryQuery`/
  `useDlqEventsQuery`/`useRequeueMutation` (TanStack Query v5), and wired
  `router.tsx` to consume `OperationsRoutes`. `main.tsx` shrank from ~3832 to
  ~3582 lines. No prerequisite gaps or bugs found this round (unlike 4d) —
  `OperationsView` was fully self-contained (no `AppOutletContext`
  dependency, no shared-but-unlisted components like the 4d
  `DocumentBlobPreview`/`EmailMetadataModal` surprise).
- Remaining: 4h through 4i (T042-T046) — `modules/upload`, Zustand/cleanup,
  remove `main.tsx`.

## Things that will bite you (4d-specific)

1. **`data-model.md`'s module→origin table is incomplete**: `DocumentBlobPreview`
   and `EmailMetadataModal` are listed under `shared`, but no task in Phase
   2/4a-4c actually moved them — they were still living in `main.tsx`'s
   "settings" section, and `ValidationView`/`DocumentTable` (moved in 4d) both
   depend on them. Had to extract them to `shared/components/` as an
   unlisted prerequisite (same pattern as the T008→T019 handoff). If you're
   doing 4e-4h and find another shared-per-data-model.md component still
   stuck in `main.tsx`, that's the same gap repeating — check before assuming
   a component doesn't need moving just because no task named it.
2. **`eslint.config.js`'s `max-lines: 150` applies to every file, not just
   components** (only `types.ts`/`shared/types/**`/`models/**`/test files are
   exempted) — a fat *hook* file trips it exactly like a fat component.
   `ValidationView` (367 lines in the monolith) needed 3 extra local-state
   hooks (`useFieldExtraction`, `useFieldVersioning`, `useDocumentDecision`,
   deliberately NOT exported from the module barrel — implementation detail of
   one screen) plus 4 sub-components before every file cleared 150 lines.
   `data-model.md` already documents `hooks/` as covering "hooks de estado
   local", not just query/mutation hooks, so this split matches the intended
   module shape, not an improvisation.
3. **Tests that `render()` a `modules/documents` component directly (not
   through `renderApp()`) now need a `QueryClientProvider`** — those
   components call `useQuery`/`useMutation`. Added `renderWithQueryClient`
   (fresh `QueryClient` per call, `retry: false`) to `src/__tests__/utils.tsx`;
   `approved.test.tsx`/`rejected.test.tsx`/`validation.test.tsx` (and the new
   `DocumentTable`/`ValidationView` a11y tests) use it. If 4e-4h add more
   directly-rendered component tests for query-backed components, use the
   same helper, not a bare `render()`.
4. **The shared `queryClient` singleton (used by `renderApp()`) had no cache
   reset between tests** — harmless while nothing used real `useQuery` caching,
   a real cross-test pollution risk now. Fixed with `queryClient.clear()` in
   `afterEach` in `src/__tests__/setup.ts`. Don't remove this.
5. **`shared/lib/queryClient.ts` now sets `defaultOptions.queries.retry:
   false`** — deliberate: the pre-migration hooks never retried a failed
   fetch, they showed the error immediately. TanStack Query's default (3
   retries with backoff) would have delayed error display by several seconds,
   a real UX regression. Don't remove this default when touching other
   modules' queries.
6. **The a11y tests found real, pre-existing WCAG gaps in code that was moved
   verbatim** (not introduced by the extraction): unlabeled bulk-select
   checkboxes in `DocumentTable`, an unlabeled schema `<select>` in
   `LangExtractPanel`, an empty `<th>` (actions column). Fixed with
   `aria-label`/`sr-only` span since FR-013/SC-006 requires WCAG AA on
   *migrated* code and the test exists specifically to catch this. Worth
   scanning for the same unlabeled-input pattern in the modules still to come
   (settings has several bare `<select>`s already, per T004's original lint
   baseline).
7. **Caught and fixed a transcription error against itself**: while copying
   `ReadOnlyTranscriptionFormatted`'s empty-state text from memory, the first
   draft used invented text ("Nenhuma transcricao formatada disponivel...").
   A line-by-line `diff` against `git show HEAD:.../main.tsx` (the
   pre-session committed version) caught it before commit — the real text is
   "Disponivel apenas para PDFs digitais processados pelo engine Docling."
   **Lesson for any future large copy/move task**: diff the extracted file
   against the last-committed original before trusting it, don't rely on
   having read it correctly earlier in the same session.

## Things that will bite you (4e-specific)

1. **Removing a section from `main.tsx` orphans its now-unused shared imports
   at the top of the file** — after deleting `OperationsView`, `formatDate`
   (from `shared/utils`) and `Metric`/`KeyValueGrid` (from `shared/components`)
   had no other consumer left in `main.tsx` and had to be dropped from the
   import lines, or `eslint`'s `no-unused-vars` fails the gate. `grep -n` for
   each named import across the whole file *before* assuming it's still used
   elsewhere — don't just delete the block and re-run lint to find out
   (`RefreshCw`/`AlertTriangle`/`FileText` all survived because other
   not-yet-extracted views still use them; only `formatDate`/`Metric`/
   `KeyValueGrid` were operations-exclusive). Expect the same check every
   remaining sub-phase (4f-4i).
2. **The diff-against-original-block verification from the 4d lesson (#7
   below) is worth doing as a matter of course, not just when something feels
   off** — for 4e, `diff`ing extracted strings/classNames/endpoints against
   `git show HEAD:.../main.tsx`'s removed block (804-1052) confirmed zero
   content drift before committing, cheap insurance against silent typos in a
   manual copy/split.
3. **No `AppOutletContext` dependency this time** — `OperationsView` never
   read `schemas`/`layouts`/`selectedDocument`/etc., so the route component
   (`OperationsRoute.tsx`) didn't need `useOutletContext` at all, unlike
   `documents`' routes. Don't assume every module route needs the context
   plumbing `documents` used — check what the original component actually
   consumed first.

## Things that will bite you (4g-specific)

1. **Resolved the item-6 plan below the other way**: T041's own text only
   says "movendo `GerenciarUsuarios`/`GerenciarRoles`" — it doesn't mention
   `TenantsView`, and `data-model.md`'s module→origin table lists `admin` as
   `GerenciarUsuarios`/`GerenciarRoles` only. Rather than expand T041's scope
   to match the old plan (which would also require updating `data-model.md`
   to keep docs/code in sync — out of scope for "only execute Phase 4g"),
   `TenantsView`/`TenantUsersPanel`/`CopySlugButton` were left in `main.tsx`
   untouched. **This means T046 (remove `main.tsx`) will hit a wall**:
   `TenantsView` still needs a home before the monolith can actually be
   deleted, and no task in `tasks.md` currently owns that move. Whoever picks
   up T042/T043/T046 needs to either add a task for it or fold it into T046
   itself (new `modules/tenants` vs. stuffing it into `modules/admin` after
   all — it's tenant-provisioning, not user/role management, so a separate
   module may fit the domain boundary better; worth a deliberate call, not a
   default).
2. **`AdminRole` still needs to leave the module barrel for `main.tsx`**:
   `TenantUsersPanel` (in `TenantsView`) types its own `api.get<AdminRole[]>
  ('/roles')` call with the same `AdminRole` interface `GerenciarRoles` uses.
   Since the interface can't be duplicated (single source of truth) and can't
   live in `main.tsx` anymore (moved to `modules/admin/types.ts`), `admin`'s
   barrel (`index.ts`) exports `AdminRole` as a type in addition to the
   contract-mandated `AdminRoutes` — a legitimate cross-module type import
   documented inline in the barrel. If `TenantsView` is ever extracted (see
   point 1), check whether this export is still needed by anything else
   before deleting it.
3. Same `isFetching`-not-`isLoading` and per-list-key-invalidation choices as
   4e's `OperationsView`/`operationsKeys` — see that section below, same
   reasoning applies verbatim to `adminKeys.users()`/`adminKeys.roles()`.

## New finding from 4c: router singleton + jsdom test bleed

`createBrowserRouter` binds to the real `window.location`/`history` at
creation time. `jsdom`'s `window` persists across `it()` blocks in the same
test file (React state resets on remount, but the URL does not) — so a
router created once at module scope and reused by every `renderApp()` call
made a test start on whatever path the *previous* test's navigation left
behind, which sometimes fired requests MSW didn't have handlers for in that
specific test. The failure mode was subtle: all tests still passed, but
Vitest reported "Unhandled Errors" (`DataCloneError`, since an `AxiosError`
with a `transformRequest` function can't be structured-cloned across the
worker RPC channel) — easy to miss if you only check the pass/fail count.

Fix: `router.tsx` exports both a factory (`createAppRouter()`) and the app's
default singleton (`router`, built from the factory, used by
`src/app/main.tsx` in production). `Root` (in `app/main.tsx`) takes an
optional `router` prop for injection. `src/__tests__/utils.tsx`'s
`renderApp()` resets `window.history` to `/` and builds a fresh router via
`createAppRouter()` on every call. **If a future module (documents/
operations/settings/admin/upload, 4d-4h) adds its own router-touching test
helper, apply the same pattern** — don't reuse a shared router instance
across tests.

## Things that will bite you if you don't know them

1. **The pre-commit hook always fails on `main.tsx`'s `max-lines` error until
   the monolith is gone (T046).** This is expected, not a regression. The user
   already authorized `--no-verify` for this specific, known cause across all
   of Phase 4 (see `86585ae`, `8322754` commit messages, and the T022 handoff
   note in tasks.md). Any *other* lint/type/test failure still blocks normally
   — only the `main.tsx` max-lines error (plus the pre-existing 11
   `exhaustive-deps` warnings) is the allowed baseline. **Confirmed again in
   the 4c session**: rather than trusting this note blindly, the agent asked
   the user explicitly before using `--no-verify` on the 4c commit (`156ff46`)
   — user picked "use --no-verify" — so this claim is verified accurate, not
   just carried over from a prior handoff. Still worth asking each time rather
   than assuming, since authorization doesn't silently extend forever.
2. **`pre-commit` wasn't installed in this devcontainer** (`.git/hooks/pre-commit`
   shells out to a binary that `post-create.sh` never installed). Fixed by
   adding `uv tool install pre-commit` to `.devcontainer/post-create.sh`.
3. **Some earlier "[X] done" task notes in tasks.md (Phase 2, T008) didn't
   match the actual code.** T008 claimed `main.tsx` was updated to import
   `api`/`authApi`/`comApi` from `shared/lib/http.ts`, but it still defined its
   own local instances until this session's T019/T020 fixed it for real (see
   the "Correção retroativa" addendum under T008 in tasks.md). Lesson: verify
   code, don't just trust a prior session's checkmark.
4. **`src/shared/lib/` is NOT gitignored** despite the root `.gitignore`'s
   broad Python-oriented `lib/` pattern (line 17) — there's already a
   `!/docuparse-project/frontend/src/shared/lib/` negation further down (with
   a comment explaining why). `git check-ignore` gives a misleading answer if
   run with a relative path from inside a subdirectory instead of the repo
   root; always double check from `/docuparser`.
5. **`shared/lib/http.ts` needs `VITE_BACKEND_CORE_URL`/`VITE_BACKEND_COM_URL`
   env support** (prod/Cloudflare Pages absolute URLs) — already fixed in
   T019, but if anyone touches `http.ts` again, don't regress it back to
   relative-only URLs.
6. **`TenantsView`/`TenantUsersPanel`/`CopySlugButton`** (multi-tenant admin UI,
   feature 010) are **not mentioned anywhere in `data-model.md`'s module
   mapping table**, but they exist in `main.tsx` and are wired into `NAV_ITEMS`
   (`tenants.manage` permission) and `AuthContextValue.switchTenant`.
   **Resolved (2026-07-24, during T041): NOT folded into `modules/admin`** —
   see "Things that will bite you (4g-specific)" point 1 above for why, and
   for what this defers onto T046.
