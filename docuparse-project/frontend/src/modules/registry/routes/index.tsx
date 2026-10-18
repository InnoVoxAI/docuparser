import type { RouteObject } from 'react-router'
import { ErrorBoundary } from '../../../shared/components'
import { ImportReviewRoute } from './ImportReviewRoute'
import { RegistryRoute } from './RegistryRoute'

export const RegistryRoutes: RouteObject[] = [
    { path: 'registry', element: <RegistryRoute />, errorElement: <ErrorBoundary /> },
    { path: 'registry-import', element: <ImportReviewRoute />, errorElement: <ErrorBoundary /> },
]
