import type { RouteObject } from 'react-router'
import { ErrorBoundary } from '../../../shared/components'
import { SettingsRoute } from './SettingsRoute'

export const SettingsRoutes: RouteObject[] = [
    { path: 'settings', element: <SettingsRoute />, errorElement: <ErrorBoundary /> },
]
