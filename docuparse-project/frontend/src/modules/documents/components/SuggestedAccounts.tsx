import { accountLabel, describeEvidence } from '../classification'
import type { AccountSuggestion } from '../schemas/classification'

/**
 * Contas que o fornecedor do documento já usou, da mais usada para a menos usada.
 * "Usar" só escolhe a conta; "Usar sempre" também cria a regra do fornecedor.
 */
export function SuggestedAccounts({
    suggestions,
    currentAccountId,
    saving,
    onChoose,
}: {
    suggestions: AccountSuggestion[]
    currentAccountId: string | undefined
    saving: boolean
    onChoose: (accountId: string, remember: boolean) => Promise<unknown>
}) {
    if (suggestions.length === 0) return null
    const choose = async (id: string, remember: boolean) => {
        try {
            await onChoose(id, remember)
        } catch {
            /* o erro da API aparece no painel */
        }
    }
    return (
        <div className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                Contas que este fornecedor já usou
            </div>
            <ul aria-label="Contas sugeridas" className="divide-y divide-zinc-100 rounded-md border border-zinc-200">
                {suggestions.map((item) => {
                    const current = item.ledger_account.id === currentAccountId
                    return (
                        <li
                            key={item.ledger_account.id}
                            className="flex flex-wrap items-center gap-2 px-2 py-1.5 text-sm"
                        >
                            <div className="min-w-0 flex-1">
                                <div className="font-medium text-zinc-900">
                                    {accountLabel(item.ledger_account)}
                                    {current ? (
                                        <span className="ml-2 text-xs font-normal text-zinc-500">(atual)</span>
                                    ) : null}
                                </div>
                                <div className="text-xs text-zinc-500">{describeEvidence(item)}</div>
                            </div>
                            {current ? null : (
                                <button
                                    type="button"
                                    disabled={saving}
                                    onClick={() => choose(item.ledger_account.id, false)}
                                    className="h-7 rounded-md border border-zinc-300 px-2 text-xs font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50"
                                >
                                    Usar
                                </button>
                            )}
                            <button
                                type="button"
                                disabled={saving}
                                onClick={() => choose(item.ledger_account.id, true)}
                                className="h-7 rounded-md bg-zinc-900 px-2 text-xs font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                            >
                                Usar sempre
                            </button>
                        </li>
                    )
                })}
            </ul>
            <p className="text-xs text-zinc-500">
                "Usar sempre" vale para este fornecedor em todos os condomínios do mesmo plano.
            </p>
        </div>
    )
}
