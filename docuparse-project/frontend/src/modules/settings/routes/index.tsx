import type { RouteObject } from 'react-router'
import { ErrorBoundary } from '../../../shared/components'
import { IntegrationsRoute } from './IntegrationsRoute'
import { SettingsRoute } from './SettingsRoute'

export const SettingsRoutes: RouteObject[] = [
    { path: 'settings', element: <SettingsRoute />, errorElement: <ErrorBoundary /> },
    { path: 'integrations', element: <IntegrationsRoute />, errorElement: <ErrorBoundary /> },
]
