import { useState } from 'react'
import { Settings, Trash2 } from 'lucide-react'
import { EmptyState } from '../../../shared/components'
import type { SchemaConfig } from '../../../types'
import { DeleteSchemaModal } from './DeleteSchemaModal'

/**
 * `onDeleted` (que antes propagava `onChanged()`) foi removido — a lista de
 * `schemas` vem de `useSchemasQuery` (invalidada automaticamente pela
 * mutação de exclusão), então este componente só precisa fechar o modal.
 *
 * `readOnly` (spec 018): o catálogo é global e só o operador de plataforma
 * (`tenants.manage`) pode excluir — para os demais, esconde o botão.
 */
export function SchemaList({ schemas, readOnly = false }: { schemas: SchemaConfig[]; readOnly?: boolean }) {
    const [targetSchema, setTargetSchema] = useState<SchemaConfig | null>(null)
    return (
        <>
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">Schemas existentes</div>
                {schemas.length === 0 ? (
                    <EmptyState icon={Settings} text="Nenhuma configuracao cadastrada." />
                ) : (
                    <div className="divide-y divide-zinc-100">
                        {schemas.map((schema) => (
                            <div key={schema.id} className="flex items-center justify-between px-4 py-3">
                                <div className="text-sm font-medium">{schema.schema_id}</div>
                                {readOnly ? null : (
                                    <button
                                        type="button"
                                        onClick={() => setTargetSchema(schema)}
                                        className="flex items-center gap-1 rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                                    >
                                        <Trash2 size={12} />
                                        Excluir
                                    </button>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </section>
            {targetSchema && <DeleteSchemaModal schema={targetSchema} onClose={() => setTargetSchema(null)} />}
        </>
    )
}
