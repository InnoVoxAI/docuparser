import { useState } from 'react'
import { Alert } from '../../../shared/components'
import { accountLabel, describeOrigin, isClassificationLocked } from '../classification'
import { useClassificationReview } from '../hooks/useClassificationReview'
import type { Document } from '../types'
import { OptionPickerForm } from './OptionPickerForm'

/**
 * Revisão da conta classificada: mostra a conta sugerida pelo motor (e por quê)
 * e deixa o operador trocá-la por outra do plano do condomínio antes da decisão.
 * A troca fica no backend como DocumentEvent (quem, de/para).
 */
export function ClassificationReviewPanel({
    document,
    onChanged,
}: {
    document: Document
    onChanged: () => void | Promise<unknown>
}) {
    const [editingCondominium, setEditingCondominium] = useState(false)
    const review = useClassificationReview({ document, editingCondominium, onChanged })
    const locked = isClassificationLocked(document.status)
    const classification = document.classification ?? null
    const condominium = document.condominium ?? null

    const saveCondominium = async (id: string) => {
        await review.condominiums.save(id)
        setEditingCondominium(false)
    }

    // Tenant que não cadastrou condomínios não usa o plano de contas: não mostra nada.
    const unused =
        !condominium &&
        !classification &&
        !review.condominiums.loading &&
        !review.condominiums.loadError &&
        review.condominiums.options.length === 0
    if (unused) return null

    return (
        <section aria-label="Classificação contábil" className="rounded-md border border-zinc-200">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">Classificação contábil</div>
            <div className="space-y-3 p-3">
                {!condominium || editingCondominium ? (
                    <div className="space-y-1">
                        <p className="text-sm text-zinc-600">
                            {condominium
                                ? 'Escolha o condomínio correto do documento.'
                                : 'Defina o condomínio do documento para sugerir a conta.'}
                        </p>
                        {review.condominiums.loadError ? (
                            <Alert tone="error">{review.condominiums.loadError}</Alert>
                        ) : null}
                        {locked ? null : (
                            <OptionPickerForm
                                label="Condomínio do documento"
                                options={review.condominiums.options.map((c) => ({ value: c.id, label: c.name }))}
                                defaultValue={condominium?.id ?? ''}
                                submitLabel="Definir condomínio"
                                loading={review.condominiums.loading}
                                saving={review.condominiums.saving}
                                error={review.condominiums.saveError}
                                onSubmit={saveCondominium}
                                onCancel={condominium ? () => setEditingCondominium(false) : undefined}
                            />
                        )}
                    </div>
                ) : (
                    <>
                        <div className="flex flex-wrap items-center gap-2 text-sm text-zinc-700">
                            <span>
                                Condomínio: <strong>{condominium.name}</strong>
                            </span>
                            {locked ? null : (
                                <button
                                    type="button"
                                    onClick={() => setEditingCondominium(true)}
                                    className="text-xs text-zinc-500 underline hover:text-zinc-800"
                                >
                                    Alterar condomínio
                                </button>
                            )}
                        </div>
                        <div className="text-sm">
                            {classification ? (
                                <>
                                    <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                                        Conta {classification.origin === 'manual' ? 'definida' : 'sugerida'}
                                    </div>
                                    <div className="font-medium text-zinc-900">
                                        {accountLabel(classification.ledger_account)}
                                    </div>
                                    <div className="text-xs text-zinc-500">{describeOrigin(classification)}</div>
                                </>
                            ) : (
                                <p className="text-zinc-600">Nenhuma conta foi sugerida. Escolha uma abaixo.</p>
                            )}
                        </div>
                        {review.accounts.loadError ? <Alert tone="error">{review.accounts.loadError}</Alert> : null}
                        {locked ? (
                            <p className="text-xs text-zinc-500">
                                O documento já foi decidido; a conta não pode mais ser alterada.
                            </p>
                        ) : (
                            <OptionPickerForm
                                key={classification?.ledger_account.id ?? 'none'}
                                label="Conta do plano de contas"
                                options={review.accounts.options.map((a) => ({ value: a.id, label: accountLabel(a) }))}
                                defaultValue={classification?.ledger_account.id ?? ''}
                                submitLabel="Alterar conta"
                                loading={review.accounts.loading}
                                saving={review.accounts.saving}
                                error={review.accounts.saveError}
                                onSubmit={review.accounts.save}
                            />
                        )}
                    </>
                )}
            </div>
        </section>
    )
}
