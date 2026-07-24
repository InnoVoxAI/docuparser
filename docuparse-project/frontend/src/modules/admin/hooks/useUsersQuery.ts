import { useQuery } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { AdminUser } from '../types'
import { adminKeys } from './queryKeys'

const EMPTY_USERS: AdminUser[] = []

async function fetchUsers(): Promise<AdminUser[]> {
    const response = await api.get<AdminUser[]>('/users')
    return response.data ?? EMPTY_USERS
}

export function useUsersQuery() {
    const query = useQuery({ queryKey: adminKeys.users(), queryFn: fetchUsers })
    return { ...query, data: query.data ?? EMPTY_USERS }
}
