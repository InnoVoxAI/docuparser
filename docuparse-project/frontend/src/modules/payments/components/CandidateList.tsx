import { useEffect, useState } from 'react'
import { EmptyState, Pagination, SearchInput } from '../../../shared/components'
import { formatDate } from '../../../shared/utils'
import { useCandidates } from '../hooks'
import type { CandidateKind, PaymentDocument } from '../schemas/payments'
import { PAGE_SIZE } from '../services/payments.service'
import { describeOrigin, formatCnpj, formatMoney } from '../utils'
import { Eye, FileX } from 'lucide-react'

const SEARCH_DELAY_MS = 300

interface Props {
    kind: CandidateKind
    title: string
    selected: PaymentDocument[]
    onToggle: (doc: PaymentDocument) => void
    /** Abre o documento num popup, para o analista conferir antes de escolher. */
    onView: (doc: PaymentDocument) => void
}

/** Documentos de um tipo que ainda não estão em nenhum agrupamento, com busca e seleção. */
export function CandidateList({ kind, title, selected, onToggle, onView }: Props) {
    const [text, setText] = useState('')
    const [search, setSearch] = useState('')
    const [page, setPage] = useState(1)
    const query = useCandidates(kind, search, page)
    const single = kind === 'invoice'

    useEffect(() => {
        const timer = setTimeout(() => {
            setSearch(text.trim())
            setPage(1)
        }, SEARCH_DELAY_MS)
        return () => clearTimeout(timer)
    }, [text])

    const results = query.data?.results ?? []
    return (
        <section aria-label={title} className="rounded-lg border border-zinc-200 bg-white">
            <header className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 px-4 py-2">
                <h2 className="text-sm font-semibold text-zinc-900">{title}</h2>
                <SearchInput value={text} onChange={setText} placeholder="Nome, CNPJ ou valor" />
            </header>
            {query.isError ? (
                <p className="px-4 py-3 text-sm text-red-700">Não foi possível carregar a lista.</p>
            ) : null}
            {!query.isLoading && !query.isError && results.length === 0 ? (
                <EmptyState icon={FileX} text="Nada sem match por aqui." />
            ) : null}
            <ul className="divide-y divide-zinc-100">
                {results.map((doc) => (
                    <li key={doc.id} className="flex items-start hover:bg-zinc-50">
                        <label className="flex min-w-0 flex-1 cursor-pointer items-start gap-3 py-2 pl-4 text-sm">
                            <input
                                type={single ? 'radio' : 'checkbox'}
                                name={`select-${kind}`}
                                aria-label={`Selecionar ${doc.original_filename}`}
                                checked={selected.some((s) => s.id === doc.id)}
                                onChange={() => onToggle(doc)}
                                className="mt-1"
                            />
                            <span className="min-w-0 flex-1">
                                <span className="block truncate font-medium text-zinc-900">
                                    {doc.original_filename}
                                </span>
                                <span className="block text-xs text-zinc-500">
                                    {formatCnpj(doc.tax_id)} · {describeOrigin(doc)} · {formatDate(doc.received_at)}
                                </span>
                            </span>
                            <span className="font-semibold tabular-nums text-zinc-900">{formatMoney(doc.amount)}</span>
                        </label>
                        <button
                            type="button"
                            aria-label={`Ver ${doc.original_filename}`}
                            title="Ver o documento"
                            onClick={() => onView(doc)}
                            className="m-2 rounded-md p-1.5 text-zinc-500 hover:bg-zinc-200 hover:text-zinc-800"
                        >
                            <Eye size={16} aria-hidden="true" />
                        </button>
                    </li>
                ))}
            </ul>
            <Pagination
                page={page}
                totalPages={query.data?.total_pages ?? 1}
                count={query.data?.count ?? 0}
                pageSize={PAGE_SIZE}
                unit={['documento', 'documentos']}
                onPageChange={setPage}
            />
        </section>
    )
}
