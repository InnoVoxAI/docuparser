import type { ReactElement } from 'react'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../modules/auth'
import { Root } from '../app/main'
import { createAppRouter } from '../app/router'
import { queryClient } from '../shared/lib/queryClient'

// Componentes de `modules/documents` renderizados isoladamente (fora da árvore
// de `renderApp()`) agora dependem de TanStack Query (useQuery/useMutation) —
// precisam de um `QueryClientProvider` próprio. Um `QueryClient` novo por
// render evita que o cache de um teste vaze para o próximo (retry desligado:
// mesmo comportamento de fetch único do hook original que substituem).
export function renderWithQueryClient(ui: ReactElement) {
    const testQueryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(<QueryClientProvider client={testQueryClient}>{ui}</QueryClientProvider>)
}

// Renderiza a árvore real da aplicação (QueryClientProvider + AuthProvider + Root),
// exatamente como em produção, exceto o bootstrap createRoot (que só roda quando
// existe #root). Reseta a URL e cria um router novo a cada chamada: o router de
// produção liga-se ao `window.location`/`history` reais, que persistem entre
// testes no mesmo jsdom — sem isso, navegação feita por um teste anterior
// vazaria como rota inicial do próximo.
export function renderApp(initialPath = '/') {
    window.history.replaceState(null, '', initialPath)
    return render(
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
                <Root router={createAppRouter()} />
            </AuthProvider>
        </QueryClientProvider>,
    )
}
