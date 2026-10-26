/** Barra das linhas selecionadas: aparece só quando há seleção. */
export function BulkBar({
    count,
    busy,
    onApprove,
    onReject,
    onClear,
}: {
    count: number
    busy: boolean
    onApprove: () => void
    onReject: () => void
    onClear: () => void
}) {
    return (
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm">
            <span>{count} selecionada(s)</span>
            <button
                type="button"
                disabled={busy}
                onClick={onApprove}
                className="h-8 rounded-md bg-zinc-900 px-3 text-xs font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
            >
                Confirmar selecionadas
            </button>
            <button
                type="button"
                disabled={busy}
                onClick={onReject}
                className="h-8 rounded-md border border-zinc-300 px-3 text-xs font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50"
            >
                Rejeitar selecionadas
            </button>
            <button type="button" onClick={onClear} className="text-xs text-zinc-500 underline">
                Limpar seleção
            </button>
        </div>
    )
}
