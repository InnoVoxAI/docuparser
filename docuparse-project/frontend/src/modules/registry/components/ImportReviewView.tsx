import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { CheckCircle2 } from 'lucide-react'
import { Alert, ConfirmDialog, EmptyState } from '../../../shared/components'
import { navPath } from '../../../shared/utils'
import { useAuth } from '../../auth'
import { useCondominiums, useImportOverview, useProposalReview } from '../hooks'
import { ENTITY_TYPES, type EntityType, type Proposal } from '../schemas/registry'
import { ENTITY_LABELS, groupByAction } from '../utils'
import { BulkResultNotice } from './BulkResultNotice'
import { ConflictDialog } from './ConflictDialog'
import { ProposalSection } from './ProposalSection'

type Pending = { decision: 'approve' | 'reject'; ids: string[] } | null

/** Confirmação do analista: o que veio do Superlógica, a diferença de cada campo e a decisão. */
export function ImportReviewView() {
    const { hasPermission } = useAuth()
    const canDecide = hasPermission('models.edit')
    const [entityType, setEntityType] = useState<EntityType>('condominium')
    const [selected, setSelected] = useState<ReadonlySet<string>>(new Set())
    const [confirming, setConfirming] = useState<Pending>(null)
    const [resolving, setResolving] = useState<Proposal | null>(null)

    const overview = useImportOverview()
    const condominiums = useCondominiums()
    const batch = overview.data?.latest_batch
    const review = useProposalReview(entityType, `${batch?.id ?? ''}:${batch?.status ?? ''}`)

    const groups = useMemo(() => groupByAction(review.page?.results ?? []), [review.page])
    const counts = overview.data?.pending_by_entity ?? {}
    const total = review.page?.count ?? 0
    const pageSize = review.page?.results.length ?? 0

    const switchTab = (next: EntityType) => {
        setEntityType(next)
        setSelected(new Set())
        review.setOffset(0)
        review.resetErrors()
    }
    const toggle = (id: string) =>
        setSelected((current) => {
            const next = new Set(current)
            if (!next.delete(id)) next.add(id)
            return next
        })
    const toggleAll = (ids: string[], checked: boolean) =>
        setSelected((current) => {
            const next = new Set(current)
            ids.forEach((id) => (checked ? next.add(id) : next.delete(id)))
            return next
        })
    const runBulk = () => {
        if (!confirming) return
        review.decideMany(confirming, {
            onSettled: () => {
                setConfirming(null)
                setSelected(new Set())
            },
        })
    }
    const resolve = (resolution: Record<string, unknown>) => {
        if (!resolving) return
        review.resolve({ id: resolving.id, resolution }, { onSuccess: () => setResolving(null) })
    }
    const localMatch = resolving
        ? condominiums.data?.find((c) => c.cnpj !== '' && c.cnpj === resolving.data.cnpj)
        : undefined

    return (
        <div className="space-y-4 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div role="tablist" aria-label="Tipo de cadastro" className="flex gap-1">
                    {ENTITY_TYPES.map((type) => (
                        <button
                            key={type}
                            role="tab"
                            type="button"
                            aria-selected={entityType === type}
                            onClick={() => switchTab(type)}
                            className={`h-9 rounded-md px-3 text-sm font-medium ${entityType === type ? 'bg-zinc-900 text-white' : 'border border-zinc-300 text-zinc-700 hover:bg-zinc-100'}`}
                        >
                            {ENTITY_LABELS[type]} ({counts[type] ?? 0})
                        </button>
                    ))}
                </div>
                <Link to={navPath('registry')} className="text-sm text-zinc-600 underline">
                    Voltar para Cadastros
                </Link>
            </div>

            {!canDecide ? (
                <Alert>Você pode consultar as propostas, mas confirmar exige permissão de edição.</Alert>
            ) : null}
            {review.loadError ? <Alert tone="error">{review.loadError}</Alert> : null}
            {review.actionError ? <Alert tone="error">{review.actionError}</Alert> : null}
            {review.bulkResult ? (
                <BulkResultNotice result={review.bulkResult} onClose={review.clearBulkResult} />
            ) : null}
            {review.loading ? <p className="text-sm text-zinc-500">Carregando propostas...</p> : null}

            {canDecide && selected.size > 0 ? (
                <div className="flex items-center gap-2 rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm">
                    <span>{selected.size} selecionada(s)</span>
                    <button
                        type="button"
                        disabled={review.busy}
                        onClick={() => setConfirming({ decision: 'approve', ids: [...selected] })}
                        className="h-8 rounded-md bg-zinc-900 px-3 text-xs font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                    >
                        Confirmar selecionadas
                    </button>
                    <button
                        type="button"
                        disabled={review.busy}
                        onClick={() => setConfirming({ decision: 'reject', ids: [...selected] })}
                        className="h-8 rounded-md border border-zinc-300 px-3 text-xs font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50"
                    >
                        Rejeitar selecionadas
                    </button>
                </div>
            ) : null}

            {!review.loading && !review.loadError && groups.length === 0 ? (
                <EmptyState icon={CheckCircle2} text="Nada pendente de confirmação nesta aba." />
            ) : null}
            {groups.map((group) => (
                <ProposalSection
                    key={group.action}
                    action={group.action}
                    items={group.items}
                    selected={selected}
                    canDecide={canDecide}
                    busy={review.busy}
                    onToggle={toggle}
                    onToggleAll={toggleAll}
                    onApprove={(proposal) => review.approve(proposal.id)}
                    onReject={(proposal) => review.reject(proposal.id)}
                    onResolve={setResolving}
                />
            ))}

            {total > pageSize || review.offset > 0 ? (
                <div className="flex items-center justify-between text-sm text-zinc-600">
                    <span>
                        {review.offset + 1} a {review.offset + pageSize} de {total}
                    </span>
                    <div className="flex gap-2">
                        <button
                            type="button"
                            disabled={review.offset === 0}
                            onClick={() => review.setOffset(Math.max(review.offset - pageSize, 0))}
                            className="h-8 rounded-md border border-zinc-300 px-3 disabled:opacity-50"
                        >
                            Anterior
                        </button>
                        <button
                            type="button"
                            disabled={review.offset + pageSize >= total}
                            onClick={() => review.setOffset(review.offset + pageSize)}
                            className="h-8 rounded-md border border-zinc-300 px-3 disabled:opacity-50"
                        >
                            Próxima
                        </button>
                    </div>
                </div>
            ) : null}

            {confirming ? (
                <ConfirmDialog
                    title={confirming.decision === 'approve' ? 'Confirmar propostas' : 'Rejeitar propostas'}
                    message={
                        confirming.decision === 'approve'
                            ? `${confirming.ids.length} proposta(s) serão aplicadas ao cadastro.`
                            : `${confirming.ids.length} proposta(s) serão rejeitadas e não voltam enquanto a fonte não mudar.`
                    }
                    confirmLabel={confirming.decision === 'approve' ? 'Confirmar' : 'Rejeitar'}
                    onConfirm={runBulk}
                    onCancel={() => setConfirming(null)}
                />
            ) : null}
            {resolving ? (
                <ConflictDialog
                    proposal={resolving}
                    local={localMatch}
                    busy={review.busy}
                    error={review.actionError}
                    onSubmit={resolve}
                    onCancel={() => setResolving(null)}
                />
            ) : null}
        </div>
    )
}
