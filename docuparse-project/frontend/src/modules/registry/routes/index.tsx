import type { RouteObject } from 'react-router'
import { ErrorBoundary } from '../../../shared/components'
import { ImportReviewRoute } from './ImportReviewRoute'
import { RegistryRoute } from './RegistryRoute'
import { RulesRoute } from './RulesRoute'

export const RegistryRoutes: RouteObject[] = [
    { path: 'registry', element: <RegistryRoute />, errorElement: <ErrorBoundary /> },
    { path: 'rules', element: <RulesRoute />, errorElement: <ErrorBoundary /> },
    { path: 'registry-import', element: <ImportReviewRoute />, errorElement: <ErrorBoundary /> },
]
