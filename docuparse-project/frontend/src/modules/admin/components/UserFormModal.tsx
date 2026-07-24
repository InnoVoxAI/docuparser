import type { FormEvent } from 'react'
import type { AdminRole } from '../types'

export interface UserFormValues {
    name: string
    email: string
    password: string
    role_id: string
}

interface UserFormModalProps {
    mode: 'create' | 'edit'
    form: UserFormValues
    roles: AdminRole[]
    error: string
    onChange: (form: UserFormValues) => void
    onSubmit: (e: FormEvent) => void
    onClose: () => void
}

export function UserFormModal({ mode, form, roles, error, onChange, onSubmit, onClose }: UserFormModalProps) {
    return (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-lg">
                <h3 className="text-lg font-semibold mb-4">
                    {mode === 'create' ? 'Novo Usuário' : 'Editar Usuário'}
                </h3>
                {error && <div className="mb-3 text-sm text-red-600">{error}</div>}
                <form onSubmit={onSubmit} className="space-y-3">
                    <input
                        value={form.name}
                        onChange={(e) => onChange({ ...form, name: e.target.value })}
                        placeholder="Nome"
                        required
                        className="w-full border border-zinc-300 rounded-md px-3 py-2 text-sm"
                    />
                    <input
                        type="email"
                        value={form.email}
                        onChange={(e) => onChange({ ...form, email: e.target.value })}
                        placeholder="E-mail"
                        required
                        className="w-full border border-zinc-300 rounded-md px-3 py-2 text-sm"
                    />
                    {mode === 'create' && (
                        <input
                            type="password"
                            value={form.password}
                            onChange={(e) => onChange({ ...form, password: e.target.value })}
                            placeholder="Senha (mín. 8 chars)"
                            required
                            minLength={8}
                            className="w-full border border-zinc-300 rounded-md px-3 py-2 text-sm"
                        />
                    )}
                    <select
                        value={form.role_id}
                        onChange={(e) => onChange({ ...form, role_id: e.target.value })}
                        required
                        className="w-full border border-zinc-300 rounded-md px-3 py-2 text-sm"
                    >
                        <option value="">Selecionar role...</option>
                        {roles.map((r) => (
                            <option key={r.id} value={r.id}>
                                {r.name}
                            </option>
                        ))}
                    </select>
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
