import { formatIsoDate, formatMoney } from '../erp'
import type { ErpSummary as ErpSummaryData } from '../schemas/erp'

/** Resumo do que será lançado: condomínio, fornecedor, conta, valor e vencimentos. */
export function ErpSummary({ summary }: { summary: ErpSummaryData }) {
    return (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-zinc-500">Condomínio</dt>
            <dd className="font-medium text-zinc-900">{summary.condominium}</dd>
            <dt className="text-zinc-500">Fornecedor</dt>
            <dd className="font-medium text-zinc-900">{summary.supplier || summary.supplier_tax_id}</dd>
            <dt className="text-zinc-500">Conta</dt>
            <dd className="font-medium text-zinc-900">{summary.account}</dd>
            <dt className="text-zinc-500">Valor</dt>
            <dd className="font-medium text-zinc-900">{formatMoney(summary.amount)}</dd>
            <dt className="text-zinc-500">{summary.installments.length > 1 ? 'Parcelas' : 'Vencimento'}</dt>
            <dd className="font-medium text-zinc-900">
                {summary.installments.map((item) => (
                    <div key={`${item.due_date}-${item.amount}`}>
                        {formatIsoDate(item.due_date)} · {formatMoney(item.amount)}
                    </div>
                ))}
            </dd>
        </dl>
    )
}
