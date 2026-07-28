import type { ReactNode } from 'react'

export function ConfirmDialog({
    title,
    message,
    confirmLabel = 'Confirmar',
    cancelLabel = 'Cancelar',
    onConfirm,
    onCancel,
}: {
    title: ReactNode
    message: ReactNode
    confirmLabel?: string
    cancelLabel?: string
    onConfirm: () => void | Promise<unknown>
    onCancel: () => void
}) {
    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
        >
            <div className="w-full max-w-sm rounded-md border border-zinc-200 bg-white p-4 shadow-lg">
                <div className="text-sm font-semibold text-zinc-900">{title}</div>
                <p className="mt-2 text-sm text-zinc-600">{message}</p>
                <div className="mt-4 flex justify-end gap-2">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="h-9 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        {cancelLabel}
                    </button>
                    <button
                        type="button"
                        onClick={onConfirm}
                        className="h-9 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700"
                    >
                        {confirmLabel}
                    </button>
                </div>
            </div>
        </div>
    )
}
