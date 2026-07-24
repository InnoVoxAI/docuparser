import { Field } from '../../../shared/components'
import type { LayoutConfig, SchemaConfig } from '../../../types'
import type { LayoutForm, SchemaForm } from '../types'
import { ConfigList } from './ConfigList'
import { HintPanel } from './HintPanel'
import { SchemaList } from './SchemaList'

export function ExtractionSetupTab({
    schemas,
    layouts,
    selectedSchemaId,
    onLoadExisting,
    onNewModel,
    schemaForm,
    setSchemaForm,
    layoutForm,
    setLayoutForm,
}: {
    schemas: SchemaConfig[]
    layouts: LayoutConfig[]
    selectedSchemaId: string
    onLoadExisting: (schemaId: string) => void
    onNewModel: () => void
    schemaForm: SchemaForm
    setSchemaForm: (form: SchemaForm) => void
    layoutForm: LayoutForm
    setLayoutForm: (form: LayoutForm) => void
}) {
    return (
        <div className="space-y-4">
            <section className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
                <div className="grid gap-3 lg:grid-cols-[minmax(260px,1fr)_220px]">
                    <Field label="Selecionar modelo existente">
                        <select
                            value={selectedSchemaId}
                            onChange={(event) => onLoadExisting(event.target.value)}
                            className="input"
                        >
                            <option value="">Criar novo modelo</option>
                            {schemas.map((schema) => (
                                <option key={schema.id} value={schema.id}>
                                    {schema.schema_id} {schema.version}
                                </option>
                            ))}
                        </select>
                    </Field>
                    <button
                        type="button"
                        onClick={onNewModel}
                        className="mt-6 h-9 rounded-md border border-zinc-300 px-3 text-sm font-medium hover:bg-zinc-100"
                    >
                        Novo modelo
                    </button>
                </div>
            </section>
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
                <div className="grid gap-3 md:grid-cols-2">
                    <Field label="Nome do modelo">
                        <input
                            value={schemaForm.model_name}
                            onChange={(event) => setSchemaForm({ ...schemaForm, model_name: event.target.value })}
                            className="input"
                            placeholder="Recibo de servico"
                        />
                    </Field>
                    <Field label="Schema">
                        <input
                            value={schemaForm.schema_id}
                            onChange={(event) => setSchemaForm({ ...schemaForm, schema_id: event.target.value })}
                            className="input"
                            placeholder="recibo_servico"
                        />
                    </Field>
                    <Field label="Versao">
                        <input
                            value={schemaForm.version}
                            onChange={(event) => setSchemaForm({ ...schemaForm, version: event.target.value })}
                            className="input"
                        />
                    </Field>
                    <Field label="Tipo de documento">
                        <select
                            value={schemaForm.document_type}
                            onChange={(event) => {
                                setSchemaForm({ ...schemaForm, document_type: event.target.value })
                                setLayoutForm({ ...layoutForm, document_type: event.target.value })
                            }}
                            className="input"
                        >
                            <option value="scanned_image">Imagem/PDF escaneado</option>
                            <option value="digital_pdf">PDF textual</option>
                            <option value="handwritten_complex">Manuscrito complexo</option>
                        </select>
                    </Field>
                    <Field label="Status">
                        <select
                            value={schemaForm.status}
                            onChange={(event) => setSchemaForm({ ...schemaForm, status: event.target.value })}
                            className="input"
                        >
                            <option value="draft">Rascunho</option>
                            <option value="testing">Em teste</option>
                            <option value="approved">Aprovado</option>
                            <option value="disabled">Desativado</option>
                        </select>
                    </Field>
                </div>
                <HintPanel
                    title="Checklist LangExtract"
                    items={[
                        'Defina o schema antes do prompt.',
                        'Use exemplos anotados para campos ambiguos.',
                        'Mantenha o trecho fonte para validacao visual.',
                        'Publique somente versoes testadas.',
                    ]}
                />
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
                <SchemaList schemas={schemas} />
                <ConfigList
                    title="Layouts existentes"
                    items={layouts}
                    primaryKey="layout"
                    secondaryKey="document_type"
                />
            </div>
        </div>
    )
}
