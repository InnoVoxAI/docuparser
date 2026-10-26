import type { BulkResult } from '../schemas/registry'

/** Resultado de uma decisão em lote: quantas passaram e por que as outras não. */
export function BulkResultNotice({ result, onClose }: { result: BulkResult; onClose: () => void }) {
    const failed = result.failed.length > 0
    return (
        <div
            role="status"
            className={`rounded-md border px-3 py-2 text-sm ${failed ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-zinc-200 bg-white text-zinc-600'}`}
        >
            <div className="flex items-start justify-between gap-2">
                <span>
                    {result.done.length} decidida(s)
                    {failed ? `, ${result.failed.length} não puderam ser concluídas:` : '.'}
                </span>
                <button type="button" onClick={onClose} className="text-xs underline">
                    Fechar
                </button>
            </div>
            {failed ? (
                <ul className="mt-1 list-disc pl-5 text-xs">
                    {result.failed.map((item) => (
                        <li key={item.id}>{item.detail}</li>
                    ))}
                </ul>
            ) : null}
        </div>
    )
}
