import type { LayoutConfig } from '../../../types'
import type { LayoutForm, SchemaForm } from '../types'

export function ActiveTemplateHeader({
    schemaForm,
    layoutForm,
    activeLayout,
    onChangeModel,
}: {
    schemaForm: SchemaForm
    layoutForm: LayoutForm
    activeLayout?: LayoutConfig
    onChangeModel: () => void
}) {
    return (
        <div className="mb-4 rounded-md border border-zinc-200 bg-zinc-50 px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <div className="text-xs font-semibold uppercase text-zinc-500">Modelo ativo</div>
                    <div className="mt-1 text-sm font-semibold text-zinc-950">
                        {schemaForm.model_name || schemaForm.schema_id || 'Modelo sem nome'}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-600">
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">
                            schema: {schemaForm.schema_id || '-'} · {schemaForm.version || '-'}
                        </span>
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">
                            layout: {activeLayout?.layout || layoutForm.layout || '-'}
                        </span>
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">
                            tipo: {schemaForm.document_type || '-'}
                        </span>
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">
                            status: {schemaForm.status || '-'}
                        </span>
                    </div>
                </div>
                <button
                    type="button"
                    onClick={onChangeModel}
                    className="h-9 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium hover:bg-zinc-100"
                >
                    Alterar modelo
                </button>
            </div>
        </div>
    )
}
