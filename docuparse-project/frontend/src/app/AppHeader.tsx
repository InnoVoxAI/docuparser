import { RefreshCw } from 'lucide-react'
import type { MouseEventHandler } from 'react'
import type { ActiveView } from '../types'
import { viewTitle } from './navigation'

export function AppHeader({
    activeView,
    onRefresh,
}: {
    activeView: ActiveView | undefined
    onRefresh: (silent?: boolean) => Promise<void>
}) {
    return (
        <header className="border-b border-zinc-200 bg-white px-4 py-4 md:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="text-xl font-semibold">{viewTitle(activeView)}</h1>
                    <p className="mt-1 text-sm text-zinc-500">Fluxo de captura, validacao e exportacao aprovado.</p>
                </div>
                <button
                    type="button"
                    // `onRefresh` recebe o MouseEvent do clique como `silent` (truthy) — comportamento
                    // pré-existente do monólito (main.tsx, preservado 1:1 na extração de T046):
                    // clicar em "Atualizar" já rodava em modo silencioso, sem `setLoading(true)`.
                    onClick={onRefresh as unknown as MouseEventHandler<HTMLButtonElement>}
                    className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                >
                    <RefreshCw size={16} aria-hidden="true" />
                    Atualizar
                </button>
            </div>
        </header>
    )
}
