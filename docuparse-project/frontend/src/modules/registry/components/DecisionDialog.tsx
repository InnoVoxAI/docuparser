import { ConfirmDialog } from '../../../shared/components'

export type DecisionRequest = { decision: 'approve' | 'reject'; ids: string[] }

/** Pede confirmação antes de aplicar ou rejeitar várias propostas de uma vez. */
export function DecisionDialog({
    request,
    onConfirm,
    onCancel,
}: {
    request: DecisionRequest
    onConfirm: () => void
    onCancel: () => void
}) {
    const approve = request.decision === 'approve'
    return (
        <ConfirmDialog
            title={approve ? 'Confirmar propostas' : 'Rejeitar propostas'}
            message={
                approve
                    ? `${request.ids.length} proposta(s) serão aplicadas ao cadastro.`
                    : `${request.ids.length} proposta(s) serão rejeitadas e não voltam enquanto a fonte não mudar.`
            }
            confirmLabel={approve ? 'Confirmar' : 'Rejeitar'}
            onConfirm={onConfirm}
            onCancel={onCancel}
        />
    )
}
