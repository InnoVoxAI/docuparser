import { ChevronLeft, ChevronRight } from 'lucide-react'

/** Controles de navegação reutilizáveis: posição, total e anterior/próxima. */
export function Pagination({
    page,
    totalPages,
    count,
    pageSize,
    onPageChange,
}: {
    page: number
    totalPages: number
    count: number
    pageSize: number
    onPageChange: (page: number) => void
}) {
    if (count === 0) return null
    const effectiveTotal = Math.max(totalPages, 1)
    const from = (page - 1) * pageSize + 1
    const to = Math.min(page * pageSize, count)
    return (
        <nav
            aria-label="Paginação de documentos"
            className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-200 px-4 py-3 text-sm"
        >
            <span className="text-zinc-500">
                Mostrando {from}–{to} de {count} {count === 1 ? 'documento' : 'documentos'}
            </span>
            <div className="flex items-center gap-2">
                <button
                    type="button"
                    onClick={() => onPageChange(page - 1)}
                    disabled={page <= 1}
                    aria-label="Página anterior"
                    className="inline-flex h-8 items-center gap-1 rounded-md border border-zinc-300 bg-white px-2 font-medium text-zinc-700 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40"
                >
                    <ChevronLeft size={16} aria-hidden="true" /> Anterior
                </button>
                <span aria-live="polite" className="px-1 text-zinc-600">
                    Página {page} de {effectiveTotal}
                </span>
                <button
                    type="button"
                    onClick={() => onPageChange(page + 1)}
                    disabled={page >= effectiveTotal}
                    aria-label="Próxima página"
                    className="inline-flex h-8 items-center gap-1 rounded-md border border-zinc-300 bg-white px-2 font-medium text-zinc-700 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40"
                >
                    Próxima <ChevronRight size={16} aria-hidden="true" />
                </button>
            </div>
        </nav>
    )
}
