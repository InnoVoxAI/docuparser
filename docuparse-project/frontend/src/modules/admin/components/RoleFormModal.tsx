import type { FormEvent } from 'react'
import type { AdminPermission } from '../types'

export interface RoleFormValues {
    name: string
    permission_codes: string[]
}

interface RoleFormModalProps {
    mode: 'create' | 'edit'
    form: RoleFormValues
    permissions: AdminPermission[]
    error: string
    onTogglePermission: (code: string) => void
    onNameChange: (name: string) => void
    onSubmit: (e: FormEvent) => void
    onClose: () => void
}

export function RoleFormModal({
    mode,
    form,
    permissions,
    error,
    onTogglePermission,
    onNameChange,
    onSubmit,
    onClose,
}: RoleFormModalProps) {
    return (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-lg">
                <h3 className="text-lg font-semibold mb-4">{mode === 'create' ? 'Nova Role' : 'Editar Role'}</h3>
                {error && <div className="mb-3 text-sm text-red-600">{error}</div>}
                <form onSubmit={onSubmit} className="space-y-3">
                    <input
                        value={form.name}
                        onChange={(e) => onNameChange(e.target.value)}
                        placeholder="Nome da role"
                        required
                        className="w-full border border-zinc-300 rounded-md px-3 py-2 text-sm"
                    />
                    <div>
                        <div className="mb-2 text-sm font-medium text-zinc-700">Permissões</div>
                        <div className="grid grid-cols-2 gap-2">
                            {permissions.map((p) => (
                                <label key={p.code} className="flex items-center gap-2 text-sm cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={form.permission_codes.includes(p.code)}
                                        onChange={() => onTogglePermission(p.code)}
                                        className="rounded"
                                    />
                                    {p.description}
                                </label>
                            ))}
                        </div>
                    </div>
                    <div className="flex gap-2 justify-end pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-sm border border-zinc-300 rounded-md"
                        >
                            Cancelar
                        </button>
                        <button type="submit" className="px-4 py-2 text-sm bg-zinc-900 text-white rounded-md">
                            Salvar
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
