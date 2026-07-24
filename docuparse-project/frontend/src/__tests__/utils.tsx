import { render } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../modules/auth'
import { Root } from '../app/main'
import { createAppRouter } from '../app/router'
import { queryClient } from '../shared/lib/queryClient'

// Renderiza a árvore real da aplicação (QueryClientProvider + AuthProvider + Root),
// exatamente como em produção, exceto o bootstrap createRoot (que só roda quando
// existe #root). Reseta a URL e cria um router novo a cada chamada: o router de
// produção liga-se ao `window.location`/`history` reais, que persistem entre
// testes no mesmo jsdom — sem isso, navegação feita por um teste anterior
// vazaria como rota inicial do próximo.
export function renderApp() {
    window.history.replaceState(null, '', '/')
    return render(
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
                <Root router={createAppRouter()} />
            </AuthProvider>
        </QueryClientProvider>,
    )
}
