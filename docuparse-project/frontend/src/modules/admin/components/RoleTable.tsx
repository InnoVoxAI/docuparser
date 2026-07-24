import type { AdminRole } from '../types'

interface RoleTableProps {
    roles: AdminRole[]
    onEdit: (role: AdminRole) => void
    onDelete: (role: AdminRole) => void
}

export function RoleTable({ roles, onEdit, onDelete }: RoleTableProps) {
    return (
        <table className="w-full text-sm border border-zinc-200 rounded-md overflow-hidden">
            <thead className="bg-zinc-50 text-zinc-600">
                <tr>
                    {['Nome', 'Permissões', 'Usuários', 'Ações'].map((h) => (
                        <th key={h} className="px-3 py-2 text-left font-medium">
                            {h}
                        </th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {roles.map((r) => (
                    <tr key={r.id} className="border-t border-zinc-100">
                        <td className="px-3 py-2 font-medium">{r.name}</td>
                        <td className="px-3 py-2 text-zinc-500 text-xs">
                            {(r.permissions || [])
                                .map((p) => (typeof p === 'string' ? p : p.description || p.code))
                                .join(', ')}
                        </td>
                        <td className="px-3 py-2">{r.users_count}</td>
                        <td className="px-3 py-2 flex gap-2">
                            <button onClick={() => onEdit(r)} className="text-xs text-zinc-600 hover:underline">
                                Editar
                            </button>
                            <button onClick={() => onDelete(r)} className="text-xs text-red-600 hover:underline">
                                Remover
                            </button>
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    )
}
