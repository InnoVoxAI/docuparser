import type { SchemaField } from '../../../types'
import type { SchemaForm } from '../types'

export function SchemaFieldsEditor({
    fields,
    onChange,
    schemaForm,
}: {
    fields: SchemaField[]
    onChange: (fields: SchemaField[]) => void
    schemaForm: SchemaForm
}) {
    const updateField = (index: number, patch: Partial<SchemaField>) => {
        onChange(fields.map((field, fieldIndex) => (fieldIndex === index ? { ...field, ...patch } : field)))
    }

    return (
        <div className="space-y-4">
            <section className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
                <div>
                    <div>
                        <div className="text-xs font-semibold uppercase text-zinc-500">Schema em edicao</div>
                        <div className="mt-1 text-sm font-semibold text-zinc-900">
                            {schemaForm.schema_id || 'novo_schema'} · {schemaForm.version || 'v1'}
                        </div>
                        <div className="mt-1 text-sm text-zinc-600">
                            Os campos abaixo pertencem ao schema definido na aba Setup. Ao salvar em Publicacao, eles
                            serao gravados nessa versao.
                        </div>
                    </div>
                </div>
            </section>
            <div className="rounded-md border border-zinc-200">
                <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                    <div className="text-sm font-semibold">Campos de saida</div>
                    <button
                        type="button"
                        onClick={() => onChange([...fields, { name: '', type: 'string', required: false, rule: '' }])}
                        className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100"
                    >
                        Adicionar
                    </button>
                </div>
                <div className="divide-y divide-zinc-100">
                    {fields.map((field, index) => (
                        <div
                            key={`${field.name}-${index}`}
                            className="grid gap-2 px-3 py-3 lg:grid-cols-[180px_140px_120px_1fr]"
                        >
                            <input
                                value={field.name}
                                onChange={(event) => updateField(index, { name: event.target.value })}
                                className="input"
                                placeholder="campo"
                            />
                            <select
                                value={field.type}
                                onChange={(event) => updateField(index, { type: event.target.value })}
                                className="input"
                            >
                                <option value="string">string</option>
                                <option value="decimal">decimal</option>
                                <option value="date">date</option>
                                <option value="cnpj">cnpj</option>
                                <option value="cpf">cpf</option>
                                <option value="enum">enum</option>
                            </select>
                            <label className="flex h-9 items-center gap-2 rounded-md border border-zinc-300 px-3 text-sm text-zinc-700">
                                <input
                                    type="checkbox"
                                    checked={field.required}
                                    onChange={(event) => updateField(index, { required: event.target.checked })}
                                />
                                Obrigatorio
                            </label>
                            <input
                                value={field.rule}
                                onChange={(event) => updateField(index, { rule: event.target.value })}
                                className="input"
                                placeholder="regra de extracao/normalizacao"
                            />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
