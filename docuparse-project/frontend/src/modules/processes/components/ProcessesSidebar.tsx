import { AlertCircle, FileText } from 'lucide-react'
import { EmptyState, Pagination, SearchInput } from '../../../shared/components'
import type { Paginated, ProcessFilter, ProcessSummary, StepKey } from '../types'

const STATUS_LABELS: Record<string, string> = {
    RECEIVED: 'Recebido',
    OCR_COMPLETED: 'OCR concluído',
    OCR_FAILED: 'Falha no OCR',
    LAYOUT_CLASSIFIED: 'Layout classificado',
    EXTRACTION_COMPLETED: 'Extração concluída',
    VALIDATION_PENDING: 'Aguardando validação',
    APPROVED: 'Aprovado',
    REJECTED: 'Rejeitado',
    ERP_INTEGRATION_REQUESTED: 'Integração ERP solicitada',
    ERP_SENT: 'Enviado ao ERP',
    ERP_FAILED: 'Falha na integração ERP',
}

const FILTER_OPTIONS: { value: ProcessFilter | ''; label: string }[] = [
    { value: '', label: 'Todos os status' },
    { value: 'fail', label: 'Com falha' },
    { value: 'pending', label: 'Pendente' },
    { value: 'completed', label: 'Concluído' },
]

const STAGE_LABELS: Record<StepKey, string> = {
    register: 'Registro',
    ocr: 'OCR',
    extraction: 'Extração',
    validation_decision: 'Validação',
}

const STAGE_OPTIONS: { value: StepKey | ''; label: string }[] = [
    { value: '', label: 'Todas as etapas' },
    { value: 'register', label: STAGE_LABELS.register },
    { value: 'ocr', label: STAGE_LABELS.ocr },
    { value: 'extraction', label: STAGE_LABELS.extraction },
    { value: 'validation_decision', label: STAGE_LABELS.validation_decision },
]

const SELECT_CLASSES =
    'h-8 min-w-[140px] flex-1 rounded-md border border-zinc-300 bg-white px-2 text-sm text-zinc-700 outline-none focus:border-zinc-500'

export function ProcessesSidebar({
    data,
    loading,
    error,
    search,
    onSearchChange,
    filter,
    onFilterChange,
    stage,
    onStageChange,
    selectedId,
    onSelect,
    onPageChange,
}: {
    data: Paginated<ProcessSummary>
    loading: boolean
    error: string
    search: string
    onSearchChange: (value: string) => void
    filter: ProcessFilter | ''
    onFilterChange: (value: ProcessFilter | '') => void
    stage: StepKey | ''
    onStageChange: (value: StepKey | '') => void
    selectedId: string | null
    onSelect: (id: string) => void
    onPageChange: (page: number) => void
}) {
    return (
        <div className="flex h-full flex-col border-r border-zinc-200 bg-white">
            <div className="space-y-2 border-b border-zinc-200 p-3">
                <SearchInput value={search} onChange={onSearchChange} placeholder="Buscar processo..." />
                <div className="flex flex-wrap gap-2">
                    <select
                        aria-label="Filtrar por status"
                        value={filter}
                        onChange={(e) => onFilterChange(e.target.value as ProcessFilter | '')}
                        className={SELECT_CLASSES}
                    >
                        {FILTER_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                    <select
                        aria-label="Filtrar por etapa"
                        value={stage}
                        onChange={(e) => onStageChange(e.target.value as StepKey | '')}
                        className={SELECT_CLASSES}
                    >
                        {STAGE_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </div>
            </div>
            {error ? <div className="p-3 text-sm text-red-600">{error}</div> : null}
            <div className="flex-1 overflow-y-auto">
                {!loading && data.results.length === 0 ? (
                    <EmptyState icon={FileText} text="Nenhum processo encontrado." />
                ) : (
                    <ul>
                        {data.results.map((process) => (
                            <li key={process.id}>
                                <button
                                    type="button"
                                    onClick={() => onSelect(process.id)}
                                    aria-current={selectedId === process.id ? 'true' : undefined}
                                    className={`flex w-full flex-col items-start gap-1 border-b border-zinc-100 px-3 py-2 text-left text-sm hover:bg-zinc-50 ${
                                        selectedId === process.id ? 'bg-zinc-100' : ''
                                    }`}
                                >
                                    <span className="flex w-full items-center gap-1.5 font-medium text-zinc-800">
                                        {process.has_error ? (
                                            <AlertCircle
                                                size={14}
                                                className="shrink-0 text-red-600"
                                                aria-label="Processo com erro"
                                            />
                                        ) : null}
                                        <span className="truncate">{process.original_filename}</span>
                                    </span>
                                    <span className="text-xs text-zinc-500">
                                        {STATUS_LABELS[process.status] ?? process.status}
                                        {' · '}
                                        {STAGE_LABELS[process.current_stage]}
                                    </span>
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
            <Pagination
                page={data.page}
                totalPages={data.total_pages}
                count={data.count}
                pageSize={data.page_size}
                onPageChange={onPageChange}
            />
        </div>
    )
}
