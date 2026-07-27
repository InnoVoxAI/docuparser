import { useQuery } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { AdminRole } from '../types'
import { adminKeys } from './queryKeys'

const EMPTY_ROLES: AdminRole[] = []

async function fetchRoles(): Promise<AdminRole[]> {
    const response = await api.get<AdminRole[]>('/roles')
    return response.data ?? EMPTY_ROLES
}

export function useRolesQuery() {
    const query = useQuery({ queryKey: adminKeys.roles(), queryFn: fetchRoles })
    return { ...query, data: query.data ?? EMPTY_ROLES }
}
