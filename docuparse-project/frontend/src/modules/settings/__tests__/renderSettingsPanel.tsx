import type { ReactElement } from 'react'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../../auth'

/**
 * Os painéis de Configurações migrados (Ocr/Email/Integration) usam
 * `useAuth()` (para `currentTenant`) e `useQuery`/GET-on-mount — precisam de
 * `AuthProvider` + `QueryClientProvider` próprios, mesmo padrão de
 * `renderWithQueryClient` (`src/__tests__/utils.tsx`) mais `AuthProvider`
 * (mesmo padrão de `LoginPage.a11y.test.tsx`). `QueryClient` novo por
 * render evita cache vazando entre testes.
 */
export function renderSettingsPanel(ui: ReactElement) {
    const testQueryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(
        <QueryClientProvider client={testQueryClient}>
            <AuthProvider>{ui}</AuthProvider>
        </QueryClientProvider>,
    )
}
