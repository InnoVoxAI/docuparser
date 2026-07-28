import type { FormEvent } from 'react'

export function TenantCreateForm({
    slug,
    name,
    submitting,
    error,
    onSlugChange,
    onNameChange,
    onSubmit,
}: {
    slug: string
    name: string
    submitting: boolean
    error: string
    onSlugChange: (value: string) => void
    onNameChange: (value: string) => void
    onSubmit: (e: FormEvent) => void
}) {
    return (
        <form onSubmit={onSubmit} className="rounded-lg border border-zinc-200 bg-white p-5">
            <h2 className="mb-4 text-sm font-semibold text-zinc-800">Novo Tenant</h2>
            <div className="flex flex-wrap gap-3">
                <input
                    type="text"
                    value={slug}
                    onChange={(e) => onSlugChange(e.target.value)}
                    required
                    maxLength={50}
                    pattern="[a-z0-9-]+"
                    placeholder="slug (ex: empresa-abc)"
                    title="Apenas letras minúsculas, números e hífens"
                    className="h-9 flex-1 min-w-40 rounded-md border border-zinc-300 px-3 text-sm focus:border-zinc-500 focus:outline-none"
                />
                <input
                    type="text"
                    value={name}
                    onChange={(e) => onNameChange(e.target.value)}
                    required
                    placeholder="Nome da empresa"
                    className="h-9 flex-1 min-w-40 rounded-md border border-zinc-300 px-3 text-sm focus:border-zinc-500 focus:outline-none"
                />
                <button
                    type="submit"
                    disabled={submitting}
                    className="h-9 rounded-md bg-zinc-900 px-4 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                >
                    {submitting ? 'Criando...' : 'Criar'}
                </button>
            </div>
            {error ? <p className="mt-2 text-xs text-red-600">{error}</p> : null}
        </form>
    )
}
