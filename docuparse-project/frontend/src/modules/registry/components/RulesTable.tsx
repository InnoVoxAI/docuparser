import type { Rule } from '../schemas/rules'
import { ORIGIN_LABELS, describeRuleEvidence, describeRuleSupplier, whyNotPrefilled } from '../rules'

const BUTTON =
    'h-7 rounded-md border border-zinc-300 px-2 text-xs font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50'

/** Uma linha por regra: fornecedor, conta, de onde veio, evidência e se pré-preenche. */
export function RulesTable({
    rules,
    canEdit,
    busy,
    onEdit,
    onToggle,
    onDelete,
}: {
    rules: Rule[]
    canEdit: boolean
    busy: boolean
    onEdit: (rule: Rule) => void
    onToggle: (rule: Rule) => void
    onDelete: (rule: Rule) => void
}) {
    return (
        <div className="overflow-x-auto rounded-md border border-zinc-200 bg-white">
            <table className="w-full text-left text-sm">
                <thead className="border-b border-zinc-200 text-xs uppercase text-zinc-500">
                    <tr>
                        <th className="px-3 py-2">Fornecedor</th>
                        <th className="px-3 py-2">Conta</th>
                        <th className="px-3 py-2">Origem</th>
                        <th className="px-3 py-2">Evidência</th>
                        <th className="px-3 py-2">Pré-preenche</th>
                        {canEdit ? <th className="px-3 py-2 text-right">Ações</th> : null}
                    </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                    {rules.map((rule) => {
                        const supplier = describeRuleSupplier(rule)
                        const reason = whyNotPrefilled(rule)
                        return (
                            <tr key={rule.id} className={rule.is_active ? '' : 'text-zinc-400'}>
                                <td className="px-3 py-2">
                                    <div className="font-medium">{supplier.title}</div>
                                    {supplier.detail ? (
                                        <div className="text-xs text-zinc-500">{supplier.detail}</div>
                                    ) : null}
                                </td>
                                <td className="px-3 py-2">
                                    {rule.ledger_account.code} · {rule.ledger_account.name}
                                </td>
                                <td className="px-3 py-2">{ORIGIN_LABELS[rule.origin] ?? rule.origin}</td>
                                <td className="px-3 py-2 tabular-nums">{describeRuleEvidence(rule)}</td>
                                <td className="px-3 py-2">
                                    {rule.prefills ? (
                                        <span className="rounded bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700 ring-1 ring-emerald-200">
                                            Sim
                                        </span>
                                    ) : (
                                        <span title={reason} className="text-xs text-zinc-500">
                                            Não
                                        </span>
                                    )}
                                </td>
                                {canEdit ? (
                                    <td className="px-3 py-2">
                                        <div className="flex justify-end gap-1">
                                            <button
                                                type="button"
                                                disabled={busy}
                                                onClick={() => onEdit(rule)}
                                                className={BUTTON}
                                            >
                                                Editar
                                            </button>
                                            <button
                                                type="button"
                                                disabled={busy}
                                                onClick={() => onToggle(rule)}
                                                className={BUTTON}
                                            >
                                                {rule.is_active ? 'Desativar' : 'Ativar'}
                                            </button>
                                            <button
                                                type="button"
                                                disabled={busy}
                                                onClick={() => onDelete(rule)}
                                                className={BUTTON}
                                            >
                                                Excluir
                                            </button>
                                        </div>
                                    </td>
                                ) : null}
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}
