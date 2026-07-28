import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Users } from 'lucide-react'
import { adminApi, api } from '../../../shared/lib/http'
import { asApiError } from '../../../shared/utils'
import type { AdminRole, TenantUser } from '../types'

export function TenantUsersPanel({ slug, currentTenant }: { slug: string; currentTenant: string | null }) {
    const [users, setUsers] = useState<TenantUser[]>([])
    const [roles, setRoles] = useState<AdminRole[]>([])
    const [loadingUsers, setLoadingUsers] = useState(true)
    const [form, setForm] = useState({ name: '', email: '', password: '', role_id: '' })
    const [submitting, setSubmitting] = useState(false)
    const [formError, setFormError] = useState('')

    const fetchUsers = useCallback(async () => {
        setLoadingUsers(true)
        try {
            const [ur, rr] = await Promise.all([
                adminApi.get<{ data: TenantUser[] }>(`/tenants/${slug}/users/`),
                api.get<AdminRole[]>('/roles'),
            ])
            setUsers(ur.data.data)
            setRoles(rr.data)
        } catch {
            /* ignore — panel shows empty */
        } finally {
            setLoadingUsers(false)
        }
    }, [slug])

    useEffect(() => {
        fetchUsers()
    }, [fetchUsers])

    const handleCreate = async (e: FormEvent) => {
        e.preventDefault()
        setFormError('')
        setSubmitting(true)
        try {
            await adminApi.post(`/tenants/${slug}/users/`, form)
            setForm({ name: '', email: '', password: '', role_id: '' })
            await fetchUsers()
        } catch (err) {
            const apiError = asApiError(err)
            const detail = apiError.response?.data?.error?.detail
            setFormError(
                apiError.response?.status === 409
                    ? (detail ?? `E-mail já em uso.`)
                    : (detail ?? 'Erro ao criar usuário.'),
            )
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="border-t border-zinc-100 bg-zinc-50 px-4 py-4 space-y-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-600 uppercase tracking-wide">
                <Users size={12} />
                Usuários do tenant {slug}
                {currentTenant === slug ? (
                    <span className="ml-1 rounded bg-blue-100 px-1.5 py-0.5 text-blue-700 normal-case font-medium">
                        contexto atual
                    </span>
                ) : null}
            </div>

            {loadingUsers ? (
                <p className="text-xs text-zinc-500">Carregando...</p>
            ) : users.length === 0 ? (
                <p className="text-xs text-zinc-400 italic">Nenhum usuário neste tenant.</p>
            ) : (
                <div className="overflow-x-auto rounded border border-zinc-200 bg-white">
                    <table className="w-full text-xs">
                        <thead>
                            <tr className="border-b border-zinc-100 text-zinc-400 text-left">
                                <th className="px-3 py-2">Nome</th>
                                <th className="px-3 py-2">E-mail</th>
                                <th className="px-3 py-2">Role</th>
                                <th className="px-3 py-2">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-50">
                            {users.map((u) => (
                                <tr key={u.id}>
                                    <td className="px-3 py-2 text-zinc-800">{u.name}</td>
                                    <td className="px-3 py-2 font-mono text-zinc-600">{u.email}</td>
                                    <td className="px-3 py-2 text-zinc-500">{u.role?.name ?? '—'}</td>
                                    <td className="px-3 py-2">
                                        <span
                                            className={`rounded-full px-1.5 py-0.5 text-xs font-medium ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-zinc-100 text-zinc-500'}`}
                                        >
                                            {u.is_active ? 'Ativo' : 'Inativo'}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <form onSubmit={handleCreate} className="rounded border border-zinc-200 bg-white p-3 space-y-2">
                <p className="text-xs font-medium text-zinc-600">Convidar usuário</p>
                <div className="flex flex-wrap gap-2">
                    <input
                        type="text"
                        value={form.name}
                        onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                        required
                        placeholder="Nome"
                        className="h-8 flex-1 min-w-28 rounded border border-zinc-300 px-2 text-xs focus:outline-none focus:border-zinc-500"
                    />
                    <input
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
                        required
                        placeholder="E-mail"
                        className="h-8 flex-1 min-w-36 rounded border border-zinc-300 px-2 text-xs focus:outline-none focus:border-zinc-500"
                    />
                    <input
                        type="password"
                        value={form.password}
                        onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
                        required
                        minLength={8}
                        placeholder="Senha (mín. 8)"
                        className="h-8 flex-1 min-w-32 rounded border border-zinc-300 px-2 text-xs focus:outline-none focus:border-zinc-500"
                    />
                    <select
                        value={form.role_id}
                        onChange={(e) => setForm((p) => ({ ...p, role_id: e.target.value }))}
                        required
                        className="h-8 flex-1 min-w-28 rounded border border-zinc-300 px-2 text-xs bg-white focus:outline-none focus:border-zinc-500"
                    >
                        <option value="">Selecionar role</option>
                        {roles.map((r) => (
                            <option key={r.id} value={r.id}>
                                {r.name}
                            </option>
                        ))}
                    </select>
                    <button
                        type="submit"
                        disabled={submitting}
                        className="h-8 rounded bg-zinc-900 px-3 text-xs font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                    >
                        {submitting ? '...' : 'Convidar'}
                    </button>
                </div>
                {formError ? <p className="text-xs text-red-600">{formError}</p> : null}
            </form>
        </div>
    )
}
