import { Alert } from '../../../shared/components'
import type { BulkResult } from '../schemas/registry'
import { BulkResultNotice } from './BulkResultNotice'

function Dismissible({ text, onClose }: { text: string; onClose: () => void }) {
    return (
        <div role="status">
            <Alert tone="success" className="">
                <div className="flex items-start justify-between gap-2">
                    <span>{text}</span>
                    <button type="button" onClick={onClose} className="text-xs underline">
                        Fechar
                    </button>
                </div>
            </Alert>
        </div>
    )
}

/** Tudo o que a tela avisa ao analista: chegada da sincronização, confirmação feita, erros e lote. */
export function ReviewNotices({
    arrival,
    notice,
    loadError,
    actionError,
    readOnly,
    bulkResult,
    onCloseArrival,
    onCloseNotice,
    onCloseBulk,
}: {
    arrival: string
    notice: string
    loadError: string
    actionError: string
    readOnly: boolean
    bulkResult: BulkResult | null
    onCloseArrival: () => void
    onCloseNotice: () => void
    onCloseBulk: () => void
}) {
    return (
        <>
            {arrival ? <Dismissible text={arrival} onClose={onCloseArrival} /> : null}
            {notice ? <Dismissible text={notice} onClose={onCloseNotice} /> : null}
            {readOnly ? (
                <Alert className="">Você pode consultar as propostas, mas confirmar exige permissão de edição.</Alert>
            ) : null}
            {loadError ? (
                <Alert tone="error" className="">
                    {loadError}
                </Alert>
            ) : null}
            {actionError ? (
                <Alert tone="error" className="">
                    {actionError}
                </Alert>
            ) : null}
            {bulkResult ? <BulkResultNotice result={bulkResult} onClose={onCloseBulk} /> : null}
        </>
    )
}
