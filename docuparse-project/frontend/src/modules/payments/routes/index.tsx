import type { RouteObject } from 'react-router'
import { ErrorBoundary } from '../../../shared/components'
import { PaymentsRoute } from './PaymentsRoute'

export const PaymentsRoutes: RouteObject[] = [
    { path: 'payments', element: <PaymentsRoute />, errorElement: <ErrorBoundary /> },
]
