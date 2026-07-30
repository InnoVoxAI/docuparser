import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../shared/lib/http'
import type { AdminUser } from '../types'
import { adminKeys } from './queryKeys'

export interface CreateUserInput {
    name: string
    email: string
    role_id: string
}

export interface UpdateUserInput {
    id: string
    name: string
    email: string
    role_id: string | null
}

async function createUser(input: CreateUserInput): Promise<void> {
    await api.post('/users', input)
}

async function updateUser({ id, ...patch }: UpdateUserInput): Promise<void> {
    await api.patch(`/users/${id}`, patch)
}

async function toggleUserActive(user: AdminUser): Promise<void> {
    await api.patch(`/users/${user.id}`, { is_active: !user.is_active })
}

async function resendInvite(userId: string): Promise<void> {
    await api.post(`/users/${userId}/invites/resend/`)
}

export function useUserMutations() {
    const queryClient = useQueryClient()
    const invalidate = () => queryClient.invalidateQueries({ queryKey: adminKeys.users() })

    const createMutation = useMutation({ mutationFn: createUser, onSuccess: invalidate })
    const updateMutation = useMutation({ mutationFn: updateUser, onSuccess: invalidate })
    const toggleMutation = useMutation({ mutationFn: toggleUserActive, onSuccess: invalidate })
    const resendInviteMutation = useMutation({ mutationFn: resendInvite, onSuccess: invalidate })

    return {
        createUser: createMutation.mutateAsync,
        updateUser: updateMutation.mutateAsync,
        toggleUserActive: toggleMutation.mutateAsync,
        resendInvite: resendInviteMutation.mutateAsync,
        isResendingInvite: resendInviteMutation.isPending,
    }
}
