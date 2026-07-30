import type { AdminUser } from '../types'

interface UserTableProps {
    users: AdminUser[]
    onEdit: (user: AdminUser) => void
    onToggleActive: (user: AdminUser) => void
    onResendInvite: (user: AdminUser) => void
    resendingUserId?: string | null
}

export function UserTable({ users, onEdit, onToggleActive, onResendInvite, resendingUserId }: UserTableProps) {
    return (
        <table className="w-full text-sm border border-zinc-200 rounded-md overflow-hidden">
            <thead className="bg-zinc-50 text-zinc-600">
                <tr>
                    {['Nome', 'E-mail', 'Role', 'Status', 'Ações'].map((h) => (
                        <th key={h} className="px-3 py-2 text-left font-medium">
                            {h}
                        </th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {users.map((u) => (
                    <tr key={u.id} className="border-t border-zinc-100">
                        <td className="px-3 py-2">{u.name}</td>
                        <td className="px-3 py-2 text-zinc-500">{u.email}</td>
                        <td className="px-3 py-2">{u.role?.name || '—'}</td>
                        <td className="px-3 py-2">
                            <span
                                className={`rounded-full px-2 py-0.5 text-xs ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-zinc-100 text-zinc-500'}`}
                            >
                                {u.is_active ? 'Ativo' : 'Inativo'}
                            </span>
                        </td>
                        <td className="px-3 py-2 flex gap-2">
                            <button onClick={() => onEdit(u)} className="text-xs text-zinc-600 hover:underline">
                                Editar
                            </button>
                            <button onClick={() => onToggleActive(u)} className="text-xs text-zinc-600 hover:underline">
                                {u.is_active ? 'Desativar' : 'Ativar'}
                            </button>
                            {u.invite_pending ? (
                                <button
                                    onClick={() => onResendInvite(u)}
                                    disabled={resendingUserId === u.id}
                                    className="text-xs text-zinc-600 hover:underline disabled:opacity-50"
                                >
                                    {resendingUserId === u.id ? 'Reenviando...' : 'Reenviar convite'}
                                </button>
                            ) : null}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    )
}
