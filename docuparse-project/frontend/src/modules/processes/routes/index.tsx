import { Navigate, type RouteObject } from 'react-router'

// A antiga tela "/processes" virou a página inicial ("/"). A rota é mantida
// só como redirect pra não quebrar links/bookmarks antigos.
export const ProcessesRoutes: RouteObject[] = [{ path: 'processes', element: <Navigate to="/" replace /> }]
