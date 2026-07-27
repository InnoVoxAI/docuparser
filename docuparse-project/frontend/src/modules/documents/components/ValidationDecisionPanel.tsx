import { CheckCircle2, ClipboardCheck, XCircle } from 'lucide-react'
import { Alert, EmptyState, StatusBadge } from '../../../shared/components'
import type { Document, FieldRow, FieldVersionsResponse, SaveMessage, SchemaConfig } from '../types'
import { DocumentMetadataPanel } from './DocumentMetadataPanel'
import { LangExtractPanel } from './LangExtractPanel'
import { ReadOnlyTranscriptionFormatted } from './ReadOnlyTranscriptionFormatted'
import { ValidationSaveControls } from './ValidationSaveControls'

export function ValidationDecisionPanel({
    selectedDocument,
    selectedDocumentId,
    schemas,
    fieldRows,
    onFieldRowsChange,
    selectedSchemaId,
    onSchemaChange,
    extracting,
    extractMessage,
    onRunExtract,
    saving,
    saveMessage,
    confirmSaveOpen,
    onOpenConfirmSave,
    onCancelConfirmSave,
    onSaveFields,
    historyOpen,
    onCloseHistory,
    history,
    historyLoading,
    historyError,
    onOpenHistory,
    notes,
    onNotesChange,
    notesError,
    submitError,
    submitting,
    onApprove,
    onReject,
}: {
    selectedDocument: Document | null
    selectedDocumentId: string
    schemas: SchemaConfig[]
    fieldRows: FieldRow[]
    onFieldRowsChange: (rows: FieldRow[]) => void
    selectedSchemaId: string
    onSchemaChange: (id: string) => void
    extracting: boolean
    extractMessage: string
    onRunExtract: () => void | Promise<unknown>
    saving: boolean
    saveMessage: SaveMessage | null
    confirmSaveOpen: boolean
    onOpenConfirmSave: () => void
    onCancelConfirmSave: () => void
    onSaveFields: () => void | Promise<unknown>
    historyOpen: boolean
    onCloseHistory: () => void
    history: FieldVersionsResponse | null
    historyLoading: boolean
    historyError: string
    onOpenHistory: () => void | Promise<unknown>
    notes: string
    onNotesChange: (value: string) => void
    notesError: boolean
    submitError: string
    submitting: boolean
    onApprove: () => void | Promise<unknown>
    onReject: () => void | Promise<unknown>
}) {
    return (
        <section className="min-h-[360px] rounded-md border border-zinc-200 bg-white p-4">
            {!selectedDocument ? (
                <EmptyState icon={ClipboardCheck} text="Selecione um documento pendente." />
            ) : (
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <StatusBadge status={selectedDocument.status} />
                    </div>
                    <DocumentMetadataPanel document={selectedDocument} />
                    {!selectedDocument.extraction_result ? (
                        <Alert>
                            {selectedDocument.status === 'OCR_COMPLETED'
                                ? 'OCR concluido. Extração de campos pendente — verifique se existe um layout configurado para este tipo de documento.'
                                : 'Documento recebido. O OCR automatico ainda nao concluiu; use Atualizar em alguns instantes.'}
                        </Alert>
                    ) : null}
                    <ReadOnlyTranscriptionFormatted value={selectedDocument.full_transcription_formatted} />
                    <LangExtractPanel
                        documentId={selectedDocumentId}
                        schemas={schemas}
                        selectedSchemaId={selectedSchemaId}
                        onSchemaChange={onSchemaChange}
                        extracting={extracting}
                        extractMessage={extractMessage}
                        onRunExtract={onRunExtract}
                        fieldRows={fieldRows}
                        onFieldRowsChange={onFieldRowsChange}
                    />
                    <ValidationSaveControls
                        saving={saving}
                        saveMessage={saveMessage}
                        confirmSaveOpen={confirmSaveOpen}
                        onOpenConfirmSave={onOpenConfirmSave}
                        onCancelConfirmSave={onCancelConfirmSave}
                        onSaveFields={onSaveFields}
                        historyOpen={historyOpen}
                        onCloseHistory={onCloseHistory}
                        history={history}
                        historyLoading={historyLoading}
                        historyError={historyError}
                        onOpenHistory={onOpenHistory}
                    />
                    <textarea
                        value={notes}
                        onChange={(event) => onNotesChange(event.target.value)}
                        className={`input min-h-[86px]${notesError ? ' border-red-500 ring-1 ring-red-500' : ''}`}
                        placeholder="Motivo da rejeição (obrigatório para rejeitar)"
                    />
                    {submitError ? <Alert tone="error">{submitError}</Alert> : null}
                    <div className="flex flex-wrap gap-2">
                        <button type="button" disabled={submitting} onClick={onApprove} className="success-button">
                            <CheckCircle2 size={16} aria-hidden="true" />
                            Aprovar
                        </button>
                        <button type="button" disabled={submitting} onClick={onReject} className="danger-button">
                            <XCircle size={16} aria-hidden="true" />
                            Rejeitar
                        </button>
                    </div>
                </div>
            )}
        </section>
    )
}
