import { useState } from 'react'
import { ClipboardCheck } from 'lucide-react'
import { Alert, EmptyState } from '../../../shared/components'
import type { Document, FieldRow, FieldVersionsResponse, SaveMessage, SchemaConfig } from '../types'
import { DocumentMetadataPanel } from './DocumentMetadataPanel'
import { LangExtractPanel } from './LangExtractPanel'
import { RejectReasonDialog } from './RejectReasonDialog'
import { ValidationActionsBar } from './ValidationActionsBar'

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
    hasUnsavedChanges,
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
    /** Salvar/Histórico só fazem sentido — e só aparecem — quando há edição
     * de campos ainda não persistida. */
    hasUnsavedChanges: boolean
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
    const [rejectDialogOpen, setRejectDialogOpen] = useState(false)

    return (
        <section className="min-h-[360px] rounded-md border border-zinc-200 bg-white p-4">
            {!selectedDocument ? (
                <EmptyState icon={ClipboardCheck} text="Selecione um documento pendente." />
            ) : (
                <div className="space-y-4">
                    {/* Tudo que a decisão precisa, no topo — não deve exigir rolar a
                    tela toda. */}
                    <ValidationActionsBar
                        status={selectedDocument.status}
                        hasUnsavedChanges={hasUnsavedChanges}
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
                        submitting={submitting}
                        onApprove={onApprove}
                        onReject={() => setRejectDialogOpen(true)}
                    />
                    {submitError && !rejectDialogOpen ? <Alert tone="error">{submitError}</Alert> : null}

                    <DocumentMetadataPanel document={selectedDocument} />
                    {!selectedDocument.extraction_result ? (
                        <Alert>
                            {selectedDocument.status === 'OCR_COMPLETED'
                                ? 'OCR concluido. Extração de campos pendente — verifique se existe um layout configurado para este tipo de documento.'
                                : 'Documento recebido. O OCR automatico ainda nao concluiu; use Atualizar em alguns instantes.'}
                        </Alert>
                    ) : null}
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
                </div>
            )}
            {rejectDialogOpen ? (
                <RejectReasonDialog
                    notes={notes}
                    onNotesChange={onNotesChange}
                    notesError={notesError}
                    submitError={submitError}
                    submitting={submitting}
                    onConfirm={onReject}
                    onCancel={() => setRejectDialogOpen(false)}
                />
            ) : null}
        </section>
    )
}
