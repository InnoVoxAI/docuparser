import type { RouteObject } from 'react-router'
import { ErrorBoundary } from '../../../shared/components'
import { UsersRoute } from './UsersRoute'
import { RolesRoute } from './RolesRoute'
import { TenantsRoute } from './TenantsRoute'

export const AdminRoutes: RouteObject[] = [
    { path: 'users', element: <UsersRoute />, errorElement: <ErrorBoundary /> },
    { path: 'roles', element: <RolesRoute />, errorElement: <ErrorBoundary /> },
    { path: 'tenants', element: <TenantsRoute />, errorElement: <ErrorBoundary /> },
]
