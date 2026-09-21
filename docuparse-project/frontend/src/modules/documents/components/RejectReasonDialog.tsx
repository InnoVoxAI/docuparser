import { Alert } from '../../../shared/components'

/** Popup exigido ao clicar em "Rejeitar" — o motivo é obrigatório (botão de
 * confirmação fica desabilitado até haver texto), em vez de validar só depois
 * do envio. */
export function RejectReasonDialog({
    notes,
    onNotesChange,
    notesError,
    submitError,
    submitting,
    onConfirm,
    onCancel,
}: {
    notes: string
    onNotesChange: (value: string) => void
    notesError: boolean
    submitError: string
    submitting: boolean
    onConfirm: () => void | Promise<unknown>
    onCancel: () => void
}) {
    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
            aria-label="Rejeitar documento"
        >
            <div className="w-full max-w-md rounded-md border border-zinc-200 bg-white p-4 shadow-lg">
                <div className="text-sm font-semibold text-zinc-900">Rejeitar documento</div>
                <p className="mt-1 text-sm text-zinc-600">Descreva o motivo da rejeição.</p>
                <textarea
                    value={notes}
                    onChange={(event) => onNotesChange(event.target.value)}
                    className={`input mt-3 min-h-[86px]${notesError ? ' border-red-500 ring-1 ring-red-500' : ''}`}
                    placeholder="Motivo da rejeição"
                />
                {submitError ? <Alert tone="error">{submitError}</Alert> : null}
                <div className="mt-4 flex justify-end gap-2">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="h-9 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        disabled={submitting || !notes.trim()}
                        onClick={onConfirm}
                        className="danger-button"
                    >
                        Confirmar rejeição
                    </button>
                </div>
            </div>
        </div>
    )
}
