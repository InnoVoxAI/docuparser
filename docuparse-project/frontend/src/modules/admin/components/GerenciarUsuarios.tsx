import { useState, type FormEvent } from 'react'
import { asApiError } from '../../../shared/utils'
import { useUsersQuery } from '../hooks/useUsersQuery'
import { useRolesQuery } from '../hooks/useRolesQuery'
import { useUserMutations } from '../hooks/useUserMutations'
import type { AdminUser } from '../types'
import { UserTable } from './UserTable'
import { UserFormModal, type UserFormValues } from './UserFormModal'

const EMPTY_FORM: UserFormValues = { name: '', email: '', password: '', role_id: '' }

export function GerenciarUsuarios() {
    const usersQuery = useUsersQuery()
    const rolesQuery = useRolesQuery()
    const { createUser, updateUser, toggleUserActive } = useUserMutations()
    const [modal, setModal] = useState<{ mode: 'create' | 'edit'; user?: AdminUser } | null>(null)
    const [form, setForm] = useState<UserFormValues>(EMPTY_FORM)
    const [error, setError] = useState('')

    const loading = usersQuery.isFetching || rolesQuery.isFetching

    const openCreate = () => {
        setForm(EMPTY_FORM)
        setModal({ mode: 'create' })
        setError('')
    }

    const openEdit = (user: AdminUser) => {
        setForm({ name: user.name, email: user.email, password: '', role_id: user.role?.id || '' })
        setModal({ mode: 'edit', user })
        setError('')
    }

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError('')
        try {
            if (modal?.mode === 'create') {
                await createUser(form)
            } else {
                await updateUser({
                    id: modal!.user!.id,
                    name: form.name,
                    email: form.email,
                    role_id: form.role_id || null,
                })
            }
            setModal(null)
        } catch (err) {
            const data = asApiError(err).response?.data
            setError(data?.detail || data?.email?.[0] || 'Erro ao salvar.')
        }
    }

    const handleToggleActive = async (user: AdminUser) => {
        try {
            await toggleUserActive(user)
        } catch (err) {
            alert(asApiError(err).response?.data?.detail || 'Erro ao alterar status.')
        }
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Usuários</h2>
                <button
                    onClick={openCreate}
                    className="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white hover:bg-zinc-700"
                >
                    Novo Usuário
                </button>
            </div>
            {loading ? (
                <div className="text-sm text-zinc-500">Carregando...</div>
            ) : (
                <UserTable users={usersQuery.data} onEdit={openEdit} onToggleActive={handleToggleActive} />
            )}
            {modal && (
                <UserFormModal
                    mode={modal.mode}
                    form={form}
                    roles={rolesQuery.data}
                    error={error}
                    onChange={setForm}
                    onSubmit={handleSubmit}
                    onClose={() => setModal(null)}
                />
            )}
        </div>
    )
}
