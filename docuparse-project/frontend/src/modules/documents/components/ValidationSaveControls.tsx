import { History, Save } from 'lucide-react'
import { Alert, ConfirmDialog } from '../../../shared/components'
import type { FieldVersionsResponse, SaveMessage } from '../types'
import { FieldVersionHistoryModal } from './FieldVersionHistoryModal'

export function ValidationSaveControls({
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
}: {
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
}) {
    return (
        <>
            <div className="flex flex-1 flex-wrap items-center gap-2">
                <button
                    type="button"
                    disabled={saving}
                    onClick={onOpenConfirmSave}
                    className="inline-flex h-9 basis-40 flex-1 items-center justify-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                >
                    <Save size={16} aria-hidden="true" />
                    {saving ? 'Salvando...' : 'Salvar Alterações'}
                </button>
                <button
                    type="button"
                    onClick={onOpenHistory}
                    className="inline-flex h-9 basis-40 flex-1 items-center justify-center gap-2 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                >
                    <History size={16} aria-hidden="true" />
                    Visualizar Histórico
                </button>
            </div>
            {saveMessage ? <Alert tone={saveMessage.tone}>{saveMessage.text}</Alert> : null}
            {confirmSaveOpen ? (
                <ConfirmDialog
                    title="Salvar alterações?"
                    message="Uma nova versão da lista de campos será criada e se tornará a versão ativa. Deseja continuar?"
                    confirmLabel="Salvar"
                    onConfirm={onSaveFields}
                    onCancel={onCancelConfirmSave}
                />
            ) : null}
            {historyOpen ? (
                <FieldVersionHistoryModal
                    history={history}
                    loading={historyLoading}
                    error={historyError}
                    onClose={onCloseHistory}
                />
            ) : null}
        </>
    )
}
