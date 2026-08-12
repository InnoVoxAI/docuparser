import type { RouteObject } from 'react-router'
import { ErrorBoundary } from '../../../shared/components'
import { UploadRoute } from './UploadRoute'

export const UploadRoutes: RouteObject[] = [
    { path: 'upload', element: <UploadRoute />, errorElement: <ErrorBoundary /> },
]
