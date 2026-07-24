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

## State (updated 2026-07-24, after Phase 4c)

- Branch: `016-frontend-architecture-refactor`. Working tree clean (after this
  session's commit).
- Sub-phases done and committed: **4a** (`86585ae`, shared UI primitives),
  **4b** (`8322754`, `modules/auth`), **4c** (`156ff46`, routing — T022-T025).
  All gates green (typecheck/lint/test/build).
- **4c implemented the plan from the handoff note below almost exactly**:
  `App()` → `AppLayout` (exported from `main.tsx`, same state/handlers,
  `<Outlet context={... satisfies AppOutletContext}/>` instead of the
  `activeView` switch); `src/app/router.tsx` (`createBrowserRouter`, one route
  per `NAV_ITEMS` id via `navPath(id) = '/' + id`, thin per-route wrapper
  components doing `useOutletContext` + `PermissionGuard`); `src/app/main.tsx`
  as the new bootstrap (`QueryClientProvider` + `AuthProvider` +
  `RouterProvider`); `index.html` repointed to it. `main.tsx` still exists,
  still exports the not-yet-extracted view components (documents/operations/
  settings/admin/upload land in 4d-4h).
- Remaining: 4d through 4i (T026-T046) — `modules/documents` (+ TanStack
  Query), `modules/operations`, `modules/settings` (+ RHF/Zod), `modules/admin`,
  `modules/upload`, Zustand/cleanup, remove `main.tsx`.

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
   (`tenants.manage` permission) and `AuthContextValue.switchTenant`. This
   session's plan is to fold them into `modules/admin` alongside
   `GerenciarUsuarios`/`GerenciarRoles` (T041) since there's no better home —
   flag this decision if anyone else picks up T041 without having seen this.
