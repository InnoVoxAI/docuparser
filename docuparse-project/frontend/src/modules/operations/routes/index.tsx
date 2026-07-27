import type { RouteObject } from 'react-router'
import { ErrorBoundary } from '../../../shared/components'
import { OperationsRoute } from './OperationsRoute'

export const OperationsRoutes: RouteObject[] = [
    { path: 'operations', element: <OperationsRoute />, errorElement: <ErrorBoundary /> },
]
