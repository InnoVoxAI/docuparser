import { ClipboardCheck } from 'lucide-react'
import { useDocumentDecision } from '../hooks/useDocumentDecision'
import { useFieldExtraction } from '../hooks/useFieldExtraction'
import { useFieldVersioning } from '../hooks/useFieldVersioning'
import type { Document, SchemaConfig } from '../types'
import { ValidationDecisionPanel } from './ValidationDecisionPanel'
import { ValidationDocumentPreview } from './ValidationDocumentPreview'

export function ValidationView({
    schemas = [],
    selectedDocument,
    selectedDocumentId,
    onValidated,
    onBackToInbox,
}: {
    schemas?: SchemaConfig[]
    selectedDocument: Document | null
    selectedDocumentId: string
    onValidated: () => void | Promise<unknown>
    onBackToInbox: () => void
}) {
    const extraction = useFieldExtraction({ schemas, selectedDocument, selectedDocumentId })
    const versioning = useFieldVersioning({
        selectedDocument,
        selectedDocumentId,
        fieldRows: extraction.fieldRows,
        setFieldRows: extraction.setFieldRows,
        onValidated,
    })
    const decision = useDocumentDecision({
        selectedDocument,
        selectedDocumentId,
        fieldRows: extraction.fieldRows,
        onValidated,
        onBackToInbox,
    })

    if (!selectedDocumentId) {
        return (
            <div className="flex flex-col items-center gap-4 py-12 text-zinc-500">
                <ClipboardCheck size={40} aria-hidden="true" />
                <p className="text-sm">Selecione um documento no Inbox para iniciar a validacao.</p>
                <button
                    type="button"
                    onClick={onBackToInbox}
                    className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700"
                >
                    Ir para o Inbox
                </button>
            </div>
        )
    }

    return (
        <div className="grid gap-4 xl:grid-cols-[minmax(360px,0.9fr)_minmax(460px,1.1fr)]">
            <ValidationDocumentPreview selectedDocument={selectedDocument} />
            <ValidationDecisionPanel
                selectedDocument={selectedDocument}
                selectedDocumentId={selectedDocumentId}
                schemas={schemas}
                fieldRows={extraction.fieldRows}
                onFieldRowsChange={extraction.setFieldRows}
                selectedSchemaId={extraction.selectedSchemaId}
                onSchemaChange={extraction.setSelectedSchemaId}
                extracting={extraction.extracting}
                extractMessage={extraction.extractMessage}
                onRunExtract={extraction.runLangExtract}
                saving={versioning.saving}
                saveMessage={versioning.saveMessage}
                confirmSaveOpen={versioning.confirmSaveOpen}
                onOpenConfirmSave={() => versioning.setConfirmSaveOpen(true)}
                onCancelConfirmSave={() => versioning.setConfirmSaveOpen(false)}
                onSaveFields={versioning.handleSaveFields}
                historyOpen={versioning.historyOpen}
                onCloseHistory={() => versioning.setHistoryOpen(false)}
                history={versioning.history}
                historyLoading={versioning.historyLoading}
                historyError={versioning.historyError}
                onOpenHistory={versioning.openHistory}
                notes={decision.notes}
                onNotesChange={(value) => {
                    decision.setNotes(value)
                    decision.setNotesError(false)
                }}
                notesError={decision.notesError}
                submitError={decision.submitError}
                submitting={decision.submitting}
                onApprove={() => decision.submitDecision('approved')}
                onReject={() => decision.submitDecision('rejected')}
            />
        </div>
    )
}
