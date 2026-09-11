import { CheckCircle2, XCircle } from 'lucide-react'
import { StatusBadge } from '../../../shared/components'
import type { DocumentStatus, FieldVersionsResponse, SaveMessage } from '../types'
import { ValidationSaveControls } from './ValidationSaveControls'

/** Linha de ações do topo da tela de Validação: status + Salvar/Histórico
 * (só quando há edição não salva) + Aprovar/Rejeitar — tudo visível sem
 * precisar rolar. Extraído de `ValidationDecisionPanel` só por linhas. */
export function ValidationActionsBar({
    status,
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
    submitting,
    onApprove,
    onReject,
}: {
    status: DocumentStatus
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
    submitting: boolean
    onApprove: () => void | Promise<unknown>
    onReject: () => void
}) {
    return (
        <div className="flex flex-col gap-2">
            {/* self-start: sem isso o badge herda o stretch do flex-col e vira
            uma faixa esticada pra largura toda da coluna. */}
            <div className="self-start">
                <StatusBadge status={status} />
            </div>
            {/* Aprovar/Rejeitar na própria linha, largura cheia do container —
            precisa ser irmã (não conter o badge) da linha de baixo pra que os
            dois pares de botão dividam a mesma largura disponível e fiquem
            do mesmo tamanho. */}
            <div className="flex flex-wrap gap-2">
                <button
                    type="button"
                    disabled={submitting}
                    onClick={onApprove}
                    className="success-button basis-40 flex-1 justify-center"
                >
                    <CheckCircle2 size={16} aria-hidden="true" />
                    Aprovar
                </button>
                <button
                    type="button"
                    disabled={submitting}
                    onClick={onReject}
                    className="danger-button basis-40 flex-1 justify-center"
                >
                    <XCircle size={16} aria-hidden="true" />
                    Rejeitar
                </button>
            </div>
            {/* Linha própria pra Salvar/Histórico, sempre com essa altura
            reservada (min-h-9 = mesma altura dos botões) mesmo vazia — sem
            isso, o conteúdo abaixo pula de lugar quando os dois aparecem. */}
            <div className="flex min-h-9 flex-wrap gap-2">
                {hasUnsavedChanges ? (
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
                ) : null}
            </div>
        </div>
    )
}
