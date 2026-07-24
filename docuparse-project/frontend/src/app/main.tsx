import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, type createBrowserRouter } from 'react-router'
import { QueryClientProvider } from '@tanstack/react-query'
import '../index.css'
import { queryClient } from '../shared/lib/queryClient'
import { AuthProvider, useAuth, LoginPage } from '../modules/auth'
import { router } from './router'

/** `router` aceita override só para isolar renders em teste (ver `src/__tests__/utils.tsx`); produção usa sempre o singleton padrão. */
export function Root({ router: routerProp }: { router?: ReturnType<typeof createBrowserRouter> } = {}) {
    const { user, loading } = useAuth()
    if (loading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-zinc-50">
                <div className="text-sm text-zinc-500">Carregando...</div>
            </div>
        )
    }
    return user ? <RouterProvider router={routerProp ?? router} /> : <LoginPage />
}

const rootElement = document.getElementById('root')
if (rootElement) {
    ReactDOM.createRoot(rootElement).render(
        <React.StrictMode>
            <QueryClientProvider client={queryClient}>
                <AuthProvider>
                    <Root />
                </AuthProvider>
            </QueryClientProvider>
        </React.StrictMode>,
    )
}
