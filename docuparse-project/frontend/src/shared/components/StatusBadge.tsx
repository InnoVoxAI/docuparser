const STATUS_LABELS: Record<string, string> = {
    RECEIVED: 'Pendente',
    OCR_COMPLETED: 'Pendente',
    OCR_FAILED: 'Pendente',
    LAYOUT_CLASSIFIED: 'Pendente',
    EXTRACTION_COMPLETED: 'Pendente',
    VALIDATION_PENDING: 'Pendente',
    APPROVED: 'Aprovado',
    REJECTED: 'Rejeitado',
    ERP_INTEGRATION_REQUESTED: 'Pendente',
    ERP_SENT: 'Pendente',
    ERP_FAILED: 'Pendente',
}

export function StatusBadge({ status }: { status?: string }) {
    const isGood = status === 'APPROVED'
    const isBad = status === 'REJECTED'
    const classes = isGood
        ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
        : isBad
          ? 'bg-red-50 text-red-700 ring-red-200'
          : 'bg-amber-50 text-amber-700 ring-amber-200'
    return (
        <span className={`inline-flex rounded px-2 py-1 text-xs font-medium ring-1 ${classes}`}>
            {(status ? STATUS_LABELS[status] : '') || status || '-'}
        </span>
    )
}
