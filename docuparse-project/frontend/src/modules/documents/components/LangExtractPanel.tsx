import { useState } from 'react'
import { Plus } from 'lucide-react'
import { AddExtractedFieldForm } from './AddExtractedFieldForm'
import { ExtractedFieldCell } from './ExtractedFieldCell'
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
    const [addingField, setAddingField] = useState(false)

    const updateValue = (index: number, value: string) => {
        onFieldRowsChange(fieldRows.map((row, rowIndex) => (rowIndex === index ? { ...row, value } : row)))
    }
    const removeRow = (index: number) => {
        onFieldRowsChange(fieldRows.filter((_, rowIndex) => rowIndex !== index))
    }
    const addRow = (name: string, value: string) => {
        onFieldRowsChange([...fieldRows, { name, value, confidence: null }])
        setAddingField(false)
    }

    return (
        <div className="rounded-md border border-zinc-200">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-200 px-3 py-2">
                <div className="text-sm font-semibold">Dados extraídos</div>
                <div className="flex items-center gap-2">
                    <select
                        aria-label="Selecionar modelo de extracao"
                        value={selectedSchemaId}
                        onChange={(e) => onSchemaChange(e.target.value)}
                        className="input min-w-0"
                        disabled={extracting}
                    >
                        <option value="">Selecione um modelo...</option>
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
                        className="flex shrink-0 items-center gap-1.5 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {extracting ? 'Rastreando...' : 'Rastrear novamente'}
                    </button>
                </div>
            </div>
            {extractMessage ? (
                <div className="border-b border-zinc-100 px-3 py-2 text-xs text-zinc-500">{extractMessage}</div>
            ) : null}
            {fieldRows.length === 0 ? (
                <div className="px-3 py-6 text-center text-sm text-zinc-400">
                    Nenhum dado extraído ainda. Selecione um modelo e clique em Rastrear novamente.
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-3 p-3 sm:grid-cols-2 lg:grid-cols-3">
                    {fieldRows.map((row, index) => (
                        <ExtractedFieldCell
                            key={`${row.name}-${index}`}
                            row={row}
                            onChangeValue={(value) => updateValue(index, value)}
                            onRemove={() => removeRow(index)}
                        />
                    ))}
                </div>
            )}
            <div className="border-t border-zinc-100 px-3 py-2">
                {addingField ? (
                    <AddExtractedFieldForm onAdd={addRow} onCancel={() => setAddingField(false)} />
                ) : (
                    <button
                        type="button"
                        onClick={() => setAddingField(true)}
                        className="flex items-center gap-1.5 rounded border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-100"
                    >
                        <Plus size={14} aria-hidden="true" />
                        Adicionar campo
                    </button>
                )}
            </div>
        </div>
    )
}
