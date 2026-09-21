import { useMemo } from 'react'
import { ClipboardCheck } from 'lucide-react'
import { useDocumentDecision } from '../hooks/useDocumentDecision'
import { useFieldExtraction } from '../hooks/useFieldExtraction'
import { useFieldVersioning } from '../hooks/useFieldVersioning'
import { deriveFieldRowsFromFields } from '../utils'
import type { Document, SchemaConfig } from '../types'
import { ValidationDecisionPanel } from './ValidationDecisionPanel'
import { ValidationDocumentPreview } from './ValidationDocumentPreview'

export function ValidationView({
    schemas = [],
    selectedDocument,
    selectedDocumentId,
    onValidated,
    onBackToInbox,
    stacked = false,
    previewFirst = false,
}: {
    schemas?: SchemaConfig[]
    selectedDocument: Document | null
    selectedDocumentId: string
    onValidated: () => void | Promise<unknown>
    onBackToInbox: () => void
    /** Força layout em coluna única (campos em cima, arquivo embaixo) — usado
     * quando a tela roda num container estreito, como o drawer da Visão Geral
     * recolhido. Ao contrário de `previewFirst`, a página rola normalmente
     * (o drawer recolhido não trava a altura). */
    stacked?: boolean
    /** Coloca o preview do arquivo na coluna esquerda em vez da direita —
     * usado quando o drawer da Visão Geral está expandido. Sem efeito em modo
     * stacked. */
    previewFirst?: boolean
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
    // Salvar/Histórico só fazem sentido quando os campos na tela divergem do
    // que está persistido — compara contra o mesmo parsing usado pra popular
    // `fieldRows` (deriveFieldRowsFromFields), não contra o mapa bruto.
    const hasUnsavedChanges = useMemo(
        () =>
            JSON.stringify(extraction.fieldRows) !==
            JSON.stringify(deriveFieldRowsFromFields(selectedDocument?.extraction_result?.fields)),
        [extraction.fieldRows, selectedDocument?.extraction_result?.fields],
    )

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

    // Só o drawer expandido roda numa altura fixa (a do drawer) — ali só a
    // lista de campos deve rolar por dentro, nunca a página toda. O drawer
    // recolhido (`stacked`) e a rota standalone de Validação mantêm o scroll
    // de página normal.
    const fillHeight = previewFirst

    const decisionPanel = (
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
            hasUnsavedChanges={hasUnsavedChanges}
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
            fillHeight={fillHeight}
        />
    )
    const documentPreview = (
        <ValidationDocumentPreview selectedDocument={selectedDocument} fillHeight={fillHeight} />
    )

    if (stacked) {
        return (
            <div className="flex flex-col gap-4">
                {decisionPanel}
                {documentPreview}
            </div>
        )
    }

    if (previewFirst) {
        // Modo expandido do drawer: painéis lado a lado, mas só quando o
        // container (não a viewport — por isso `@container`/`@[...]`, já que
        // esse painel roda dentro dos 80% de largura do drawer, não da tela
        // toda) tem espaço pras duas larguras mínimas + gap (852px). Abaixo
        // disso cai pra coluna única (campos com rolagem própria em cima,
        // preview numa altura fixa embaixo) — uma divisão via `flex-wrap`
        // bagunçaria a altura porque um item sozinho numa linha não fica
        // limitado à altura da linha.
        return (
            <div className="@container h-full min-h-0">
                <div className="flex h-full min-h-0 flex-col gap-8 @[880px]:flex-row">
                    {/* Empilhado (estreito): mesma ordem do modo `stacked` —
                    campos em cima, preview embaixo. Lado a lado (largo):
                    `order` inverte pra preview ficar à esquerda. */}
                    <div className="min-h-0 flex-1 @[880px]:order-2 @[880px]:min-w-[460px] @[880px]:flex-[1.1]">
                        {decisionPanel}
                    </div>
                    <div className="h-72 shrink-0 @[880px]:order-1 @[880px]:h-auto @[880px]:min-w-[360px] @[880px]:shrink @[880px]:flex-[0.9]">
                        {documentPreview}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="grid gap-4 xl:grid-cols-[minmax(460px,1.1fr)_minmax(360px,0.9fr)]">
            {decisionPanel}
            {documentPreview}
        </div>
    )
}
