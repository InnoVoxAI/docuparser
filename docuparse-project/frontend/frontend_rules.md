# frontend.md — Project Intelligence File

> This file is the source of truth for every AI agent and contributor working on this codebase.
> Read it fully before writing any code. Follow every directive unless the user explicitly overrides one in the current session.

---

## 🏗️ Project Stack

| Layer         | Choice                                         |
| ------------- | ---------------------------------------------- |
| Framework     | React 19                                       |
| Language      | TypeScript (strict mode)                       |
| Styling       | Tailwind CSS v4                                |
| Routing       | React Router v7 (file-based, module-scoped)    |
| Data Fetching | TanStack Query v5 (`useQuery` / `useMutation`) |
| Global State  | Zustand (lightweight slices per domain)        |
| Forms         | React Hook Form + Zod                          |
| HTTP Client   | Axios (typed, with interceptors)               |
| Testing       | Vitest + React Testing Library                 |
| Bundler       | Vite                                           |

> If any package above has a clearly superior modern alternative at the time of implementation, flag it with a comment before proceeding.

---

## 📁 Folder Structure

under frontend folder:

```
src/
├── app/                    # App shell: routing, providers, ErrorBoundary
│   ├── App.tsx
│   ├── Router.tsx
│   └── providers/
├── modules/                # Feature modules — one folder per domain
│   ├── auth/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   ├── types.ts
│   │   └── index.ts        # Public API of the module
│   └── [feature]/
│       └── ...             # Same structure per module
├── shared/
│   ├── components/         # Truly reusable, domain-agnostic UI
│   ├── hooks/              # Generic hooks (useDebounce, useLocalStorage…)
│   ├── lib/                # Third-party configs (axios instance, queryClient…)
│   ├── types/              # Global TypeScript types and interfaces
│   └── utils/              # Pure utility functions
└── styles/
    └── globals.css         # Tailwind base + custom CSS variables
```

### Module Rules

- **Each module owns its own components, hooks, services, store slice, and types.**
- Modules must **never import from each other directly**. Use `shared/` as the bridge or lift shared logic there explicitly.
- Each module's `index.ts` is the **only public interface** — import from the module barrel, not from internal paths.
- Route-level lazy loading is **mandatory** for every module:
    ```tsx
    const AuthModule = React.lazy(() => import('@/modules/auth'))
    ```

---

## 🧱 Architecture Principles

### 1. Separation of Concerns

- **UI components** render only — no business logic, no direct API calls.
- **Custom hooks** own data fetching, side effects, and state derivation.
- **Services** (`*.service.ts`) own the raw API calls and data mapping — they are plain async functions, not classes.
- **Store slices** (`*.store.ts`) own UI state and derived client state. Never store server state in Zustand — that is TanStack Query's job.

### 2. Component Design

- Prefer **small, composable components** over large monolithic ones.
- Maximum ~150 lines per component file. If it grows beyond that, extract sub-components or hooks.
- Props interfaces are **always explicitly typed** — no implicit `any`, no spreading unknown objects into components.
- Use `React.memo` only when profiling confirms a performance issue — not by default.

### 3. Typing

- Enable **strict mode** in `tsconfig.json` — no exceptions.
- No `any`. Use `unknown` + type narrowing when the type is truly uncertain.
- Zod schemas are the single source of truth for runtime validation. Infer TypeScript types from them:
    ```ts
    const userSchema = z.object({ id: z.string(), name: z.string() })
    type User = z.infer<typeof userSchema>
    ```
- API response types live in `modules/[feature]/types.ts` and are always validated at the service boundary.

---

## 🎨 Styling Rules (Tailwind CSS)

- Use **Tailwind utility classes** directly in JSX. No CSS modules, no inline `style` props (except for dynamic values that Tailwind cannot express).
- Define design tokens (colors, radii, spacing, fonts) in `tailwind.config.ts` under `theme.extend` — not hardcoded in components.
- Use `@apply` in `globals.css` **only** for globally repeated patterns (e.g., `.btn-primary`). Prefer composing a React component over a CSS abstraction.
- Dark mode: use Tailwind's `dark:` variant via `class` strategy (controlled by a theme store in Zustand).
- Responsive design: mobile-first. Use `sm:`, `md:`, `lg:` breakpoints intentionally.
- No magic numbers in class strings (e.g., avoid `w-[347px]`). If a one-off value is needed, define it in the config first.

---

## ⚠️ Error Handling

### Query / Mutation Screens

- Every screen using `useQuery` or `useMutation` **must** handle all three states explicitly:
    ```tsx
    if (isLoading) return <LoadingSpinner />
    if (isError) return <ErrorMessage error={error} />
    return <MyContent data={data} />
    ```
- Use `<Suspense>` + `suspense: true` in query options as an alternative when the layout supports it.
- `useMutation` errors must be caught and shown via a toast or inline error — never silently swallowed.

### Error Boundaries

- Place an `<ErrorBoundary>` at the **layout level** (wrapping each module's route subtree).
- Use a custom `ErrorBoundary` class component with a graceful fallback UI — not just "Something went wrong."
- Log errors to the console (and to a monitoring service if configured) inside `componentDidCatch`.

### User-Facing Messages

- Never expose raw `Error` objects, API error codes, or stack traces in the UI.
- Map known API error codes to human-readable messages in a `src/shared/utils/errorMessages.ts` map.
- Unknown errors fall back to a generic, friendly message: _"Something went wrong. Please try again."_

---

## 🔄 Data Fetching Conventions (TanStack Query)

- Define all query keys in a **centralized key factory** per module:
    ```ts
    // modules/users/hooks/queryKeys.ts
    export const userKeys = {
        all: ['users'] as const,
        list: (filters: UserFilters) => [...userKeys.all, 'list', filters] as const,
        detail: (id: string) => [...userKeys.all, 'detail', id] as const,
    }
    ```
- Services are called inside `queryFn` and `mutationFn` — never called directly from components.
- `staleTime` should be set explicitly on every `useQuery` call. Don't rely on the global default.
- Optimistic updates are acceptable for mutations that affect list or detail queries — use `onMutate` / `onError` / `onSettled`.

---

## 📋 Forms (React Hook Form + Zod)

- All forms are validated with a Zod schema passed to `zodResolver`.
- Form state lives **entirely in React Hook Form** — do not mirror it in component state or Zustand.
- Submit handlers receive typed, validated data — treat it as guaranteed correct inside the handler.
- Show field-level errors using `formState.errors` — never build custom validation logic outside Zod.

---

## 🧪 Testing

- Every **service function** must have unit tests mocking the HTTP client.
- Every **custom hook** involving async logic must have integration tests using `renderHook` + MSW mocks.
- Every **critical UI component** must have at least one smoke test asserting it renders without crashing.
- Tests live in `__tests__/` inside each module folder, mirroring the source structure.
- Do not test implementation details — test behavior from the user's perspective.

---

## ✅ Code Quality Checklist

Before submitting any code, verify:

- [ ] No `any` types introduced
- [ ] Loading and error states handled in every screen with async data
- [ ] No direct cross-module imports (always via `index.ts` barrel)
- [ ] New reusable logic lives in `shared/`, not duplicated across modules
- [ ] All new Tailwind values defined in `tailwind.config.ts`, not hardcoded
- [ ] New query keys added to the module's key factory
- [ ] Zod schema exists for any new API response shape
- [ ] At least a smoke test for new components; unit tests for new services/hooks
- [ ] No raw error objects exposed in the UI

---

## 🚫 Anti-Patterns — Never Do These

| ❌ Anti-Pattern                                    | ✅ Correct Approach                         |
| -------------------------------------------------- | ------------------------------------------- |
| `import X from '@/modules/auth/components/Form'`   | `import X from '@/modules/auth'`            |
| Fetching data directly inside a component          | Use a custom hook with `useQuery`           |
| Storing server data in Zustand                     | Let TanStack Query own server state         |
| `catch (e) { console.log(e) }` with no UI feedback | Show a user-friendly error message          |
| Hardcoded colors in `className` (`text-[#3B82F6]`) | Use a Tailwind design token                 |
| God components > 150 lines                         | Extract sub-components and hooks            |
| `any` type                                         | `unknown` + type narrowing or proper typing |
| `useEffect` for data fetching                      | `useQuery`                                  |

---

## 🗣️ Communication Style for AI Agents

- **Prefer doing over asking.** If something is ambiguous but a reasonable default exists, implement the default and leave a `// NOTE:` comment explaining the assumption.
- When a directive in this file conflicts with a user instruction in the active session, **the session instruction wins** — but flag the deviation.
- When generating new modules, always scaffold the full structure (`components/`, `hooks/`, `services/`, `types.ts`, `index.ts`) even if most files start empty.
- Add `TODO:` comments when intentionally leaving something incomplete. Never leave dead code silently.
