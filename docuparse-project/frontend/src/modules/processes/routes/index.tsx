import type { RouteObject } from 'react-router'
import { ErrorBoundary } from '../../../shared/components'
import { ProcessesRoute } from './ProcessesRoute'

export const ProcessesRoutes: RouteObject[] = [
    { path: 'processes', element: <ProcessesRoute />, errorElement: <ErrorBoundary /> },
]
