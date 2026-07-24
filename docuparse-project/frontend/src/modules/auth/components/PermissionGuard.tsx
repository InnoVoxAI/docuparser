import type { ReactNode } from 'react'
import { useAuth } from '../context'

export function PermissionGuard({
    code,
    children,
    fallback = null,
}: {
    code: string
    children: ReactNode
    fallback?: ReactNode
}) {
    const { hasPermission } = useAuth()
    return hasPermission(code) ? children : fallback
}
