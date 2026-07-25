---
title: 016 Frontend Architecture Refactor — Phase 4 (US2) / Phase 5 (US3) progress
type: note
permalink: features/016-frontend-architecture-refactor-phase4
tags: [frontend, refactor, 016]
---

# 016 Frontend Architecture Refactor — Phase 4 (US2) / Phase 5 (US3) progress

Written by an agent session that was interrupted mid-task ("vou continuar com
outro agente para evitar drift"). Full detail lives in
`docs/specs/016-frontend-architecture-refactor/tasks.md` (per-task `Resultado`
notes) — this note is a pointer + the non-obvious things worth remembering.

## State (updated 2026-07-25, after Phase 4i — Phase 4 / US2 fully complete)

## State update (2026-07-25, Phase 6 / US4 — T051-T052 done)

Phase 6 is a pure retrospective/documentation phase (no code changes). T051
audited `git log main..016-frontend-architecture-refactor` and confirmed
T018/T020/T025/T032/T035/T039/T041/T042/T046/T047 are each an isolated commit
scoped to exactly one sub-phase, with green-gate evidence already in each
task's own `tasks.md` "Resultado" note — no big-bang commit spanning multiple
sub-phases anywhere. **One real deviation found**: T010 (React 18→19) and
T011 (Tailwind v3→v4) each say "commit isolado" in their own task text, but
both landed inside the single Phase 2 commit (`125e788`) together with
T004-T009. The safety property (gate green before proceeding) held — T010/T011
each have their own documented green-gate note — only the commit-granularity
instruction wasn't followed literally for those two. Not corrected
retroactively (rewriting history already built on top of would be riskier
than documenting the exception).

T052 drafted the incremental-delivery PR description (commit → sub-phase
table, the T010/T011 finding, review guide) at
`docs/specs/016-frontend-architecture-refactor/pr-description.md`. **Branch
still not pushed to `origin`, no PR open** — asked the user how to handle
"document in the PR" given there's no PR yet and `gh` isn't installed in this
environment; user chose "just draft the content, don't push/open a PR". Copy
`pr-description.md`'s content into the PR body whenever the branch does get
pushed.

Remaining: **Phase 7 (Polish, T053-T056)** — quickstart.md touch-ups, tightening
`any`/`unknown` escapes in shared types + DLQ types, final production build,
one last full manual regression pass.

- Branch: `016-frontend-architecture-refactor`.
- Sub-phases done: **4a** (`86585ae`, shared UI primitives), **4b**
  (`8322754`, `modules/auth`), **4c** (`156ff46`, routing — T022-T025), **4d**
  (`42d9c9e`, `modules/documents` + TanStack Query — T026-T033), **4e**
  (`cba0358`, `modules/operations` + TanStack Query — T034-T035), **4f**
  (`9c55ef4`, `modules/settings` + RHF/Zod — T036-T040), **4g**
  (`20e01cd`, `modules/admin` + TanStack Query — T041), **4h** (`e68a841`,
  `modules/upload` — T042), **4i** (uncommitted as of this note —
  T043-T046: Zustand review/skip, `LoginPage` RHF+Zod, `errorMessages.ts`
  applied to newly-migrated code, `src/main.tsx` **deleted**). All gates
  green (typecheck/lint/test/build) at each step. **`src/main.tsx` no longer
  exists** — Phase 4 checkpoint ("arquitetura-alvo integralmente implantada")
  reached. **Phase 5 (T047-T050, module-boundary lint enforcement + CI gate)
  is also done now** — see "State update (2026-07-25, Phase 5 / US3 —
  T047-T050 done)" section below. Remaining: Phase 6 (T051-T052, retrospective
  commit-history check) and Phase 7 (Polish, T053-T056).
- **4h** was the simplest sub-phase so far: `UploadView` (91 lines) had no
  TanStack Query conversion, no size-limit split, and no `AppOutletContext`
  surprises — moved verbatim into `modules/upload/components/`, one
  `UploadRoute.tsx` (same `PermissionGuard`/`useOutletContext<AppOutletContext>`
  pattern as `modules/documents`' routes, since it still needs `refreshData`
  from the not-yet-removed `main.tsx` context), barrel only exports
  `UploadRoutes` (module has no server state of its own). `router.tsx` lost
  its last inline route component (`useAppContext`/`useOutletContext` are now
  gone from that file entirely — every route is `...XRoutes` spread). Only
  orphaned imports in `main.tsx` this round: `EmptyState`/`Field`/`FileText`/
  `comApi`. `main.tsx`: 712 → 687 lines.
- **Pre-commit `--no-verify` used again for 4h** (`e68a841`) — same
  documented, expected-until-T046 `main.tsx` max-lines failure. Asked the
  user explicitly before bypassing (per the standing note below to not
  assume authorization carries forward); user confirmed yes.
- **Also caught this round**: `prettier --write` (part of the pre-commit
  hook) reformatted two *unrelated* already-committed files
  (`modules/admin/components/UserFormModal.tsx`/`UserTable.tsx`, pre-existing
  formatting drift from 4g, not touched by 4h's diff) when the failing
  `frontend-eslint` hook ran first and the commit was retried. Reverted both
  with `git checkout --` before committing, per `CLAUDE.md`'s "keep unrelated
  formatting changes out of the patch" guardrail. **Worth checking `git
  status` for drive-by reformats any time a hook with `--write`/`--fix` runs
  and the commit doesn't succeed on the first try.**
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
- **4i (T043-T046) is done** — Zustand review found nothing to do (skipped,
  as the task explicitly allows), `LoginPage` converted to RHF+Zod,
  `errorMessages.ts` verified already-formalized since T019, and
  `src/main.tsx` deleted for good. See "Things that will bite you
  (4i-specific)" below for the two real gotchas: where `TenantsView` ended
  up, and a module-boundary trap in `AppOutletContext`/`navPath` that would
  have poisoned T047 (Phase 5) if left as originally planned.

## State update (2026-07-25, Phase 5 / US3 — T047-T050 done)

Phase 4i's uncommitted work (T043-T046, `src/main.tsx` deletion) got committed
as `0a585b2` at some point during this session (not by this agent — noticed
because `git status` unexpectedly went from a long uncommitted list to just
`eslint.config.js` mid-session; verified via `git log` that the commit message
matches T043-T046's description, so nothing was lost). Phase 5 itself (T047-
T050) was executed on top of that commit; only `eslint.config.js` (T047) and
the new `.github/workflows/frontend-ci.yaml` (T050) are this session's actual
changes — see per-task `Resultado` notes in `tasks.md` for full detail. The two
things worth remembering that aren't obvious from the config diff alone:

1. **`eslint-plugin-boundaries` v7.1.0's default import resolver silently
   resolves nothing for this project** unless `settings['import/resolver'] =
   { node: { extensions: ['.js','.jsx','.ts','.tsx'] } }` is set explicitly —
   without it, every local `.ts`/`.tsx` import is classified "unknown", and
   since `checkUnknownLocals` defaults to `false`, the `boundaries/dependencies`
   rule silently checks *nothing* (0 errors, but not because the code is
   compliant — because the rule never evaluated a single real dependency).
   `npm run lint` reporting clean is **not sufficient proof** the boundary
   rule works; verify with `ESLINT_PLUGIN_BOUNDARIES_DEBUG=1 npx eslint
   <file>` and check `to.file.path` isn't `null` for a known-existing target
   before trusting a clean run. If this project's ESLint or plugin version
   ever bumps, re-verify this resolver setting is still needed/correct.
2. **The plugin's "internal" dependency exemption (auto-skipped, no policy
   needed) only covers files in the exact same directory** — `_isInternal`
   compares `element.path` (the file's *dirname*, not its captured module
   name) for equality. Two files in the same module but different
   subfolders (e.g. `modules/settings/routes/SettingsRoute.tsx` importing
   `modules/settings/components/SettingsView.tsx`) are **not** "internal" and
   fall straight into ordinary policy evaluation. This project's module
   element uses `capture: ['moduleName']`, so an explicit policy was added
   using the (currently non-deprecated) legacy template syntax
   `captured: { moduleName: '{{from.moduleName}}' }` to allow any file within
   the same module to import any other file in that module regardless of
   subfolder — without this, T047 reported ~65 false-positive errors across
   every module's own `routes/index.tsx` → `components/*` and similar
   same-module, different-folder imports. If a new module is added later and
   T047's rule starts erroring on its own internal cross-folder imports,
   this is almost certainly why — the exception rule (last policy in
   `eslint.config.js`'s `boundaries/dependencies` policies array) must stay
   *after* the generic "module can only be entered via index.ts" disallow
   rule for last-write-wins ordering to work.
3. **T050's CI gate needs `npm ci --legacy-peer-deps`, not plain `npm ci`** —
   confirmed by running `npm ci` from a clean `node_modules` locally: it fails
   on the same `@testing-library/react@14` (peer `react@^18`) vs. React 19
   conflict documented since T010/T011. `.github/workflows/frontend-ci.yaml`
   passes the flag explicitly; don't drop it when touching that workflow.
4. **`.github/workflows/ci.yaml` is a backend-only *deploy* pipeline** (image
   build/push for the 4 backends) that has excluded
   `docuparse-project/frontend/**` from its trigger paths since `a6c2235` —
   T050 did **not** touch that file. A brand-new, separate workflow
   (`frontend-ci.yaml`) was added instead, triggered on its own
   `docuparse-project/frontend/**` path filter (push to main/staging +
   pull_request). If someone later wants a single unified CI file, that's a
   deliberate decision to make, not a default.

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

## Things that will bite you (4h-specific)

1. **Not every sub-phase has hidden gaps** — 4h was a clean, uneventful
   extraction: no `data-model.md` surprises (unlike 4d's
   `DocumentBlobPreview`/`EmailMetadataModal`), no size-limit split needed
   (unlike 4d/4e/4g's container+presentational splits), no TanStack Query
   conversion (module has zero server-list state — a bare `POST`, no
   `useQuery`). Don't assume every remaining sub-phase needs the same
   depth of investigation; check the actual component first, the way 4e's
   note about "no `AppOutletContext` dependency this time" already
   established.
2. **`router.tsx` no longer has any inline route component** after this
   task — the last one (`UploadRoute`) is gone, along with the
   `useAppContext()`/`useOutletContext` helper that only it used. If you're
   touching `router.tsx` for 4i/T046, expect it to be just imports +
   `createAppRouter()` + `IndexRedirect` + `TenantsRoute` (the latter still
   there because of the unresolved 4g gap above).

## Things that will bite you (4i-specific)

1. **`TenantsView` landed in `modules/admin`, not a new `modules/tenants`** —
   the 4g note above explicitly flagged this as "worth a deliberate call, not
   a default" and leaned toward a separate module. Decided `admin` instead:
   tenant provisioning is permission-gated platform administration exactly
   like users/roles (`PermissionGuard code="tenants.manage"`, same shape as
   `users.manage`/`roles.manage`), it already depended on `AdminRole` before
   this move, and it has zero server-state hooks of its own (plain axios
   calls, no TanStack Query conversion asked for by any task) — spinning up
   a whole new module shape (`hooks/`, `services/`, `store/`, barrel) for one
   screen with no query layer felt disproportionate to what T046 actually
   asked for. `TenantsView` (222 lines) was split into a container +
   `TenantCreateForm`/`TenantsTable`/`TenantRow` (+ `TenantUsersPanel`/
   `CopySlugButton`, each their own file) to clear the 200-line/file limit.
   The `AdminRole` type export that the `admin` barrel carried *only* for
   `main.tsx`'s benefit (4g finding #2) is gone now — `TenantsView` imports
   `AdminRoleRef`/`TenantUser` (new type, `modules/admin/types.ts`) from
   inside the module, no cross-module export needed for it anymore.
2. **The real trap wasn't `TenantsView`, it was `AppOutletContext`/`navPath`**:
   both were still imported from `../main` by `modules/documents`' and
   `modules/upload`'s route files (`InboxRoute`/`DashboardRoute`/
   `ValidationRoute`/`UploadRoute`). The "obvious" move — relocate both into
   `src/app/` alongside `AppLayout` — would have made those domain-module
   route files import from `app/*`, which `contracts/module-boundaries.md`
   explicitly forbids ("app → modules, never the inverse") and which T047
   (Phase 5, module-boundary lint) would enforce as an error on its very
   first run. Fixed by moving `AppOutletContext` into `src/types.ts` (next to
   `Document`/`Tenant` — already a `shared/*`-equivalent file every module
   imports from directly) and `navPath` into `shared/utils/navPath.ts`
   (`app/navigation.ts` re-exports it so nothing inside `app/` had to change
   its own imports). **If T047 ever reports a boundary violation pointing at
   `app/AppLayout` or `app/navigation` from inside a `modules/*` route file,
   this is the pattern that regressed** — check `types.ts`/`shared/utils`
   still own these before assuming something new broke.
3. **`AppLayout`'s original ~180-line JSX + the `AppOutletContext` interface
   would have blown the 200-line/file limit as a single file** once moved out
   of `main.tsx` (where the limit was already the one documented "expected"
   error, exempt by virtue of the whole file being scheduled for deletion).
   Split into `navigation.ts` (pure data: `NAV_ITEMS`/`activeViewForPath`/
   `viewTitle`), `NavButton.tsx`, `AppSidebar.tsx`, `MobileNav.tsx`,
   `AppHeader.tsx`, and a much smaller `AppLayout.tsx` container (~140
   lines). The "Atualizar" button's `refreshData as unknown as
   MouseEventHandler` cast (a pre-existing quirk — clicking it always calls
   `refreshData` with the click event as a truthy `silent` arg, so it never
   shows the loading banner) was preserved verbatim in `AppHeader.tsx` with a
   comment explaining why — don't "fix" this without checking whether the
   silent-refresh behavior on manual click is actually relied upon anywhere.
4. **First sub-phase where a real browser check was possible**: Playwright
   was already installed in `node_modules` (unlike 4c/4d/etc. where it had to
   be installed ad-hoc and wasn't always available) — used to drive
   `npm run dev` headlessly with `page.route()` mocking `/api/auth/me`,
   `/api/admin/tenants/`, `/api/admin/tenants/acme/users/`, `/api/ocr/roles`,
   plus a forged JWT in `localStorage` to bypass real login. Confirmed the
   authenticated shell, sidebar nav to `/tenants`, the tenants table, the
   per-tenant users panel (row expand), and a **real page reload on
   `/tenants`** all work with zero console errors — the one console error
   that did show up (`pattern="[a-z0-9-]+"` invalid-regex warning on the
   tenant-slug inputs) was confirmed pre-existing via `git show
   HEAD:.../main.tsx` before this task touched anything, so left alone as
   out-of-scope for a move-only task. Worth fixing in a future pass (probably
   dropping the `pattern` attribute or switching to `\-` escaping) but not
   folded into T046.
5. **`errorMessages.ts` (T045) was already fully formalized since T019** — a
   grep across the repo for `err as {` and `response?.status` outside
   `shared/utils` found exactly one remaining offender: the `TenantsView`/
   `TenantUsersPanel` code this same task was about to move. So T045's actual
   work was verification + a small fix folded into T046's migration, not a
   standalone refactor — don't expect a separate diff for T045 if you go
   looking for one in the commit history.

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
