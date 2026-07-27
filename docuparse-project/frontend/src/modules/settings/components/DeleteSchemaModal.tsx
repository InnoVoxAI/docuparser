import { useState } from 'react'
import { readError } from '../../../shared/utils'
import type { SchemaConfig } from '../../../types'
import { useSchemaMutations } from '../hooks/useSchemaMutations'
import { PROTECTED_SCHEMA_IDS } from '../types'

/**
 * Exclusão convertida para `useSchemaMutations().deleteSchema` (invalida
 * `settingsKeys.all`) — `onDeleted` (que antes também disparava
 * `onChanged()`/`refreshData()` do pai) vira só `onClose`, já que a
 * atualização da lista de schemas agora é automática via invalidação de
 * query (decisão #7 do handoff de T036-T040).
 */
export function DeleteSchemaModal({ schema, onClose }: { schema: SchemaConfig; onClose: () => void }) {
    const { deleteSchema, deleting } = useSchemaMutations()
    const [error, setError] = useState('')

    if (schema.schema_id && PROTECTED_SCHEMA_IDS.includes(schema.schema_id)) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                <div className="w-full max-w-md rounded-lg border border-zinc-200 bg-white p-6 shadow-xl">
                    <div className="text-sm font-semibold text-zinc-900">Modelo protegido</div>
                    <p className="mt-2 text-sm text-zinc-600">
                        O modelo <span className="font-medium">{schema.schema_id}</span> é padrão do sistema e não pode
                        ser excluído.
                    </p>
                    <div className="mt-4 flex justify-end">
                        <button
                            type="button"
                            onClick={onClose}
                            className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium hover:bg-zinc-100"
                        >
                            Fechar
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    async function handleDelete() {
        setError('')
        try {
            await deleteSchema(schema.id)
            onClose()
        } catch (err) {
            setError(readError(err, 'Erro ao excluir o modelo. Tente novamente.'))
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="w-full max-w-md rounded-lg border border-zinc-200 bg-white p-6 shadow-xl">
                <div className="text-sm font-semibold text-zinc-900">Excluir modelo</div>
                <p className="mt-2 text-sm text-zinc-600">
                    Tem certeza que deseja excluir o modelo <span className="font-medium">{schema.schema_id}</span>?
                    Esta ação não pode ser desfeita.
                </p>
                {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
                <div className="mt-4 flex justify-end gap-2">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={deleting}
                        className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium hover:bg-zinc-100 disabled:opacity-50"
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={handleDelete}
                        disabled={deleting}
                        className="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                    >
                        {deleting ? 'Excluindo...' : 'Excluir'}
                    </button>
                </div>
            </div>
        </div>
    )
}
