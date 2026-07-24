import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { AdminRole } from '../types'
import { adminKeys } from './queryKeys'

export interface RoleFormInput {
    name: string
    permission_codes: string[]
}

async function createRole(input: RoleFormInput): Promise<void> {
    await api.post('/roles', input)
}

async function updateRole({ id, ...patch }: RoleFormInput & { id: string }): Promise<void> {
    await api.patch(`/roles/${id}`, patch)
}

async function deleteRole(role: AdminRole): Promise<void> {
    await api.delete(`/roles/${role.id}`)
}

export function useRoleMutations() {
    const queryClient = useQueryClient()
    const invalidate = () => queryClient.invalidateQueries({ queryKey: adminKeys.roles() })

    const createMutation = useMutation({ mutationFn: createRole, onSuccess: invalidate })
    const updateMutation = useMutation({ mutationFn: updateRole, onSuccess: invalidate })
    const deleteMutation = useMutation({ mutationFn: deleteRole, onSuccess: invalidate })

    return {
        createRole: createMutation.mutateAsync,
        updateRole: updateMutation.mutateAsync,
        deleteRole: deleteMutation.mutateAsync,
    }
}
