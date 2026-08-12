import type { FieldRow, SchemaConfig } from '../types'

export function LangExtractPanel({
    documentId,
    schemas,
    selectedSchemaId,
    onSchemaChange,
    extracting,
    extractMessage,
    onRunExtract,
    fieldRows,
    onFieldRowsChange,
}: {
    documentId: string
    schemas: SchemaConfig[]
    selectedSchemaId: string
    onSchemaChange: (id: string) => void
    extracting: boolean
    extractMessage: string
    onRunExtract: () => void | Promise<unknown>
    fieldRows: FieldRow[]
    onFieldRowsChange: (rows: FieldRow[]) => void
}) {
    const updateRow = (index: number, patch: Partial<FieldRow>) => {
        onFieldRowsChange(fieldRows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)))
    }
    const removeRow = (index: number) => {
        onFieldRowsChange(fieldRows.filter((_, rowIndex) => rowIndex !== index))
    }

    return (
        <div className="rounded-md border border-zinc-200">
            <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                <div className="text-sm font-semibold">Campos extraidos</div>
                <button
                    type="button"
                    onClick={() => onFieldRowsChange([...fieldRows, { name: '', value: '', confidence: null }])}
                    className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100"
                >
                    Adicionar
                </button>
            </div>
            <div className="flex flex-wrap items-center gap-2 border-b border-zinc-200 px-3 py-3">
                <select
                    aria-label="Selecionar modelo de extracao"
                    value={selectedSchemaId}
                    onChange={(e) => onSchemaChange(e.target.value)}
                    className="input min-w-0 flex-1"
                    disabled={extracting}
                >
                    <option value="">Selecione um modelo de extracao...</option>
                    {schemas.map((s) => (
                        <option key={s.id} value={s.id}>
                            {s.schema_id} ({s.version})
                        </option>
                    ))}
                </select>
                <button
                    type="button"
                    disabled={!selectedSchemaId || !documentId || extracting}
                    onClick={onRunExtract}
                    className="flex items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                >
                    {extracting ? 'Extraindo...' : 'Executar Extracao'}
                </button>
            </div>
            {extractMessage ? (
                <div className="border-b border-zinc-100 px-3 py-2 text-xs text-zinc-500">{extractMessage}</div>
            ) : null}
            {fieldRows.length === 0 ? (
                <div className="px-3 py-6 text-center text-sm text-zinc-400">
                    Selecione um modelo e clique em Executar Extracao para extrair os campos do documento.
                </div>
            ) : (
                <div className="divide-y divide-zinc-100">
                    {fieldRows.map((row, index) => (
                        <div
                            key={`${row.name}-${index}`}
                            className="grid gap-2 px-3 py-3 md:grid-cols-[220px_1fr_auto_auto]"
                        >
                            <input
                                value={row.name}
                                onChange={(event) => updateRow(index, { name: event.target.value })}
                                className="input"
                                placeholder="campo"
                            />
                            <input
                                value={row.value}
                                onChange={(event) => updateRow(index, { value: event.target.value })}
                                className="input"
                                placeholder="valor"
                            />
                            <input
                                readOnly
                                value={row.confidence != null ? `Confianca: ${(row.confidence * 100).toFixed(0)}%` : ''}
                                className="input w-32 cursor-default bg-zinc-50 text-zinc-500"
                                placeholder="—"
                                tabIndex={-1}
                            />
                            <button
                                type="button"
                                onClick={() => removeRow(index)}
                                className="h-9 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-600 hover:bg-zinc-100"
                            >
                                Remover
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
