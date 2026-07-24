import type { RouteObject } from 'react-router'
import { ErrorBoundary } from '../../../shared/components'
import { DashboardRoute } from './DashboardRoute'
import { InboxRoute } from './InboxRoute'
import { ValidationRoute } from './ValidationRoute'

export const DocumentsRoutes: RouteObject[] = [
    { path: 'dashboard', element: <DashboardRoute />, errorElement: <ErrorBoundary /> },
    { path: 'inbox', element: <InboxRoute />, errorElement: <ErrorBoundary /> },
    { path: 'validation', element: <ValidationRoute />, errorElement: <ErrorBoundary /> },
]
