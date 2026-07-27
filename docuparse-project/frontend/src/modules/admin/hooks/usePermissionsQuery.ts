import { useQuery } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { AdminPermission } from '../types'
import { adminKeys } from './queryKeys'

const EMPTY_PERMISSIONS: AdminPermission[] = []

async function fetchPermissions(): Promise<AdminPermission[]> {
    const response = await api.get<AdminPermission[]>('/permissions')
    return response.data ?? EMPTY_PERMISSIONS
}

export function usePermissionsQuery() {
    const query = useQuery({ queryKey: adminKeys.permissions(), queryFn: fetchPermissions })
    return { ...query, data: query.data ?? EMPTY_PERMISSIONS }
}
