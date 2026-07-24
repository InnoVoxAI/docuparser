import { useState, type FormEvent } from 'react'
import { asApiError } from '../../../shared/utils'
import { useRolesQuery } from '../hooks/useRolesQuery'
import { usePermissionsQuery } from '../hooks/usePermissionsQuery'
import { useRoleMutations } from '../hooks/useRoleMutations'
import type { AdminRole } from '../types'
import { RoleTable } from './RoleTable'
import { RoleFormModal, type RoleFormValues } from './RoleFormModal'

const EMPTY_FORM: RoleFormValues = { name: '', permission_codes: [] }

export function GerenciarRoles() {
    const rolesQuery = useRolesQuery()
    const permissionsQuery = usePermissionsQuery()
    const { createRole, updateRole, deleteRole } = useRoleMutations()
    const [modal, setModal] = useState<{ mode: 'create' | 'edit'; role?: AdminRole } | null>(null)
    const [form, setForm] = useState<RoleFormValues>(EMPTY_FORM)
    const [error, setError] = useState('')

    const loading = rolesQuery.isFetching || permissionsQuery.isFetching

    const openCreate = () => {
        setForm(EMPTY_FORM)
        setModal({ mode: 'create' })
        setError('')
    }

    const openEdit = (role: AdminRole) => {
        setForm({
            name: role.name,
            permission_codes: (role.permissions || []).map((p) => (typeof p === 'string' ? p : p.code)),
        })
        setModal({ mode: 'edit', role })
        setError('')
    }

    const togglePermission = (code: string) =>
        setForm((f) => ({
            ...f,
            permission_codes: f.permission_codes.includes(code)
                ? f.permission_codes.filter((c) => c !== code)
                : [...f.permission_codes, code],
        }))

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError('')
        try {
            if (modal?.mode === 'create') {
                await createRole(form)
            } else {
                await updateRole({ id: modal!.role!.id, ...form })
            }
            setModal(null)
        } catch (err) {
            const data = asApiError(err).response?.data
            setError(data?.detail || data?.permission_codes?.[0] || 'Erro ao salvar.')
        }
    }

    const handleDelete = async (role: AdminRole) => {
        if (!window.confirm(`Remover role "${role.name}"?`)) return
        try {
            await deleteRole(role)
        } catch (err) {
            alert(asApiError(err).response?.data?.detail || 'Erro ao remover.')
        }
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Roles e Permissões</h2>
                <button
                    onClick={openCreate}
                    className="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white hover:bg-zinc-700"
                >
                    Nova Role
                </button>
            </div>
            {loading ? (
                <div className="text-sm text-zinc-500">Carregando...</div>
            ) : (
                <RoleTable roles={rolesQuery.data} onEdit={openEdit} onDelete={handleDelete} />
            )}
            {modal && (
                <RoleFormModal
                    mode={modal.mode}
                    form={form}
                    permissions={permissionsQuery.data}
                    error={error}
                    onTogglePermission={togglePermission}
                    onNameChange={(name) => setForm((f) => ({ ...f, name }))}
                    onSubmit={handleSubmit}
                    onClose={() => setModal(null)}
                />
            )}
        </div>
    )
}
