import { useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { Alert, SearchInput } from '../../../shared/components'
import { navPath } from '../../../shared/utils'
import { useAuth } from '../../auth'
import { useCondominiums, useImportOverview, useProposalReview } from '../hooks'
import { useSelection } from '../hooks/useSelection'
import type { EntityType, Proposal } from '../schemas/registry'
import {
    ENTITY_LABELS,
    REVIEW_TAB_ORDER,
    describeProposal,
    firstTabWithPending,
    groupByAction,
    matchesSearch,
    pendingTotal,
    summarizePending,
} from '../utils'
import { BulkBar } from './BulkBar'
import { ConflictDialog } from './ConflictDialog'
import { DecisionDialog, type DecisionRequest } from './DecisionDialog'
import { ProposalSection } from './ProposalSection'
import { ReviewEmpty } from './ReviewEmpty'
import { ReviewNotices } from './ReviewNotices'
import { ReviewPager } from './ReviewPager'
import { ReviewSummary } from './ReviewSummary'
import { ReviewTabs } from './ReviewTabs'

/** Confirmação do analista: o que veio do Superlógica, a diferença de cada campo e a decisão. */
export function ImportReviewView() {
    const { hasPermission } = useAuth()
    const canDecide = hasPermission('models.edit')
    const cameFromSync = Boolean((useLocation().state as { fromSync?: boolean } | null)?.fromSync)
    const [chosenTab, setChosenTab] = useState<EntityType | null>(null)
    const { selected, toggle, toggleAll, clear: clearSelection } = useSelection()
    const [confirming, setConfirming] = useState<DecisionRequest | null>(null)
    const [resolving, setResolving] = useState<Proposal | null>(null)
    const [search, setSearch] = useState('')
    const [notice, setNotice] = useState('')
    const [arrivalOpen, setArrivalOpen] = useState(cameFromSync)

    const overview = useImportOverview()
    const condominiums = useCondominiums()
    const batch = overview.data?.latest_batch
    const counts = overview.data?.pending_by_entity ?? {}
    // Abre na primeira aba com pendências: o plano precisa ser confirmado antes de quem depende dele.
    const entityType = chosenTab ?? firstTabWithPending(counts)
    const review = useProposalReview(
        entityType,
        `${batch?.id ?? ''}:${batch?.status ?? ''}`,
        chosenTab !== null || Boolean(overview.data),
    )

    const results = review.page?.results ?? []
    const visible = useMemo(() => results.filter((p) => matchesSearch(p, search)), [results, search])
    const groups = useMemo(() => groupByAction(visible), [visible])
    const total = review.page?.count ?? 0
    const partial = total > results.length
    const scopeLabel = search ? 'os filtrados' : partial ? 'os desta página' : 'todos'
    const nextTab = REVIEW_TAB_ORDER.find((type) => type !== entityType && (counts[type] ?? 0) > 0)
    const allDone = Boolean(overview.data) && pendingTotal(overview.data) === 0

    const goToTab = (next: EntityType) => {
        setArrivalOpen(false)
        setChosenTab(next)
        setSearch('')
        setNotice('')
        clearSelection()
        review.resetErrors()
        review.setOffset(0)
    }
    const decide = (proposal: Proposal, decision: 'approve' | 'reject') => {
        const title = describeProposal(proposal).title
        const label = decision === 'approve' ? 'Confirmado' : 'Rejeitado'
        const run = decision === 'approve' ? review.approve : review.reject
        setArrivalOpen(false)
        run(proposal.id, { onSuccess: () => setNotice(`${label}: ${title}`) })
    }
    const runBulk = () => {
        if (!confirming) return
        setArrivalOpen(false)
        review.decideMany(confirming, {
            onSettled: () => {
                setConfirming(null)
                clearSelection()
            },
        })
    }
    const resolve = (resolution: Record<string, unknown>) => {
        if (!resolving) return
        setArrivalOpen(false)
        review.resolve(
            { id: resolving.id, resolution },
            {
                onSuccess: (resolved) => {
                    setResolving(null)
                    setNotice(`Conflito resolvido para ${resolved.length} registro(s).`)
                },
            },
        )
    }
    const localMatch = resolving
        ? condominiums.data?.find((c) => c.cnpj !== '' && c.cnpj === resolving.data.cnpj)
        : undefined
    const arrival =
        arrivalOpen && overview.data
            ? `Sincronização concluída: ${summarizePending(overview.data.pending_by_action)}. Comece pelos planos de contas.`
            : ''

    return (
        <div className="space-y-4 p-4">
            <div className="sticky top-0 z-10 -mx-4 space-y-3 bg-zinc-50 px-4 py-3 md:pr-16">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <ReviewTabs active={entityType} counts={counts} onChange={goToTab} />
                    <Link to={navPath('registry')} className="text-sm text-zinc-600 underline">
                        Voltar para Cadastros
                    </Link>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <ReviewSummary overview={overview.data} />
                    <SearchInput
                        value={search}
                        onChange={(value) => {
                            setSearch(value)
                            clearSelection()
                        }}
                        placeholder="Buscar nome ou CNPJ"
                    />
                </div>
                <ReviewNotices
                    arrival={arrival}
                    notice={notice}
                    loadError={review.loadError}
                    actionError={review.actionError}
                    readOnly={!canDecide}
                    bulkResult={review.bulkResult}
                    onCloseArrival={() => setArrivalOpen(false)}
                    onCloseNotice={() => setNotice('')}
                    onCloseBulk={review.clearBulkResult}
                />
                {canDecide && selected.size > 0 ? (
                    <BulkBar
                        count={selected.size}
                        busy={review.busy}
                        onApprove={() => setConfirming({ decision: 'approve', ids: [...selected] })}
                        onReject={() => setConfirming({ decision: 'reject', ids: [...selected] })}
                        onClear={clearSelection}
                    />
                ) : null}
            </div>

            {entityType === 'condominium' && (counts.chart ?? 0) > 0 ? (
                <Alert>
                    Há {counts.chart} plano(s) de contas pendente(s). Confirme-os antes dos condomínios: sem o plano, a
                    confirmação do condomínio é recusada.{' '}
                    <button type="button" onClick={() => goToTab('chart')} className="font-medium underline">
                        Ir para {ENTITY_LABELS.chart}
                    </button>
                </Alert>
            ) : null}
            {review.loading ? <p className="text-sm text-zinc-500">Carregando propostas...</p> : null}
            {!review.loading && !review.loadError && results.length === 0 ? (
                <ReviewEmpty
                    allDone={allDone}
                    nextTab={nextTab}
                    nextCount={nextTab ? (counts[nextTab] ?? 0) : 0}
                    onGoToNext={() => nextTab && goToTab(nextTab)}
                />
            ) : null}
            {results.length > 0 && visible.length === 0 ? (
                <p className="text-sm text-zinc-500">Nenhuma proposta corresponde à busca nesta página.</p>
            ) : null}
            {groups.map((group) => (
                <ProposalSection
                    key={group.action}
                    action={group.action}
                    items={group.items}
                    selected={selected}
                    canDecide={canDecide}
                    busy={review.busy}
                    scopeLabel={scopeLabel}
                    onToggle={toggle}
                    onToggleAll={toggleAll}
                    onApprove={(proposal) => decide(proposal, 'approve')}
                    onReject={(proposal) => decide(proposal, 'reject')}
                    onResolve={setResolving}
                    onApproveAll={(ids) => setConfirming({ decision: 'approve', ids })}
                />
            ))}

            <ReviewPager offset={review.offset} shown={results.length} total={total} onChange={review.setOffset} />

            {confirming ? (
                <DecisionDialog request={confirming} onConfirm={runBulk} onCancel={() => setConfirming(null)} />
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
