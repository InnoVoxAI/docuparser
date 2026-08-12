import { Field } from '../../../shared/components'
import type { SchemaConfig } from '../../../types'
import type { LayoutForm } from '../types'

export function ExtractionPublishTab({
    schemaDefinition,
    schemaIdValid,
    onCreateSchema,
    layoutForm,
    setLayoutForm,
    schemas,
    onCreateLayout,
}: {
    schemaDefinition: unknown
    schemaIdValid: boolean
    onCreateSchema: () => void | Promise<unknown>
    layoutForm: LayoutForm
    setLayoutForm: (form: LayoutForm) => void
    schemas: SchemaConfig[]
    onCreateLayout: () => void | Promise<unknown>
}) {
    return (
        <div className="grid gap-4 xl:grid-cols-2">
            <section className="rounded-md border border-zinc-200 p-4">
                <div className="mb-3 text-sm font-semibold">Salvar modelo como schema</div>
                <pre className="max-h-[360px] overflow-auto rounded-md bg-zinc-950 p-3 text-xs text-zinc-50">
                    {JSON.stringify(schemaDefinition, null, 2)}
                </pre>
                <button
                    type="button"
                    onClick={onCreateSchema}
                    disabled={!schemaIdValid}
                    className="primary-button mt-3"
                >
                    Salvar schema LangExtract
                </button>
            </section>
            <section className="rounded-md border border-zinc-200 p-4">
                <div className="mb-3 text-sm font-semibold">Vincular layout ao schema</div>
                <div className="grid gap-3 md:grid-cols-2">
                    <Field label="Layout">
                        <input
                            value={layoutForm.layout}
                            onChange={(event) => setLayoutForm({ ...layoutForm, layout: event.target.value })}
                            className="input"
                        />
                    </Field>
                    <Field label="Tipo documento">
                        <input
                            value={layoutForm.document_type}
                            onChange={(event) => setLayoutForm({ ...layoutForm, document_type: event.target.value })}
                            className="input"
                        />
                    </Field>
                    <Field label="Schema">
                        <select
                            value={layoutForm.schema_config_id}
                            onChange={(event) => setLayoutForm({ ...layoutForm, schema_config_id: event.target.value })}
                            className="input"
                        >
                            <option value="">Selecionar</option>
                            {schemas.map((schema) => (
                                <option key={schema.id} value={schema.id}>
                                    {schema.schema_id} {schema.version}
                                </option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Confianca minima">
                        <input
                            value={layoutForm.confidence_threshold}
                            onChange={(event) =>
                                setLayoutForm({ ...layoutForm, confidence_threshold: event.target.value })
                            }
                            className="input"
                        />
                    </Field>
                </div>
                <button
                    type="button"
                    onClick={onCreateLayout}
                    disabled={!layoutForm.layout.trim() || !layoutForm.schema_config_id}
                    className="primary-button mt-3"
                >
                    Criar layout
                </button>
            </section>
        </div>
    )
}
