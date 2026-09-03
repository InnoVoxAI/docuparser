import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Alert } from '../../../shared/components'
import { useProcessPipelineQuery } from '../hooks/useProcessPipelineQuery'
import { processKeys } from '../hooks/queryKeys'
import { ProcessBreakdown } from './ProcessBreakdown'
import { IngestionLogsModal } from './IngestionLogsModal'
import { ValidationDrawer } from './ValidationDrawer'

type OpenPanel = 'logs' | 'validation' | null

/** Conteúdo expandido de uma linha da tabela: busca o pipeline do processo e
 * mostra as 4 caixas (Em fila → Ingestão → Validação → Classificação). */
export function ProcessRowDetail({ documentId }: { documentId: string }) {
    const queryClient = useQueryClient()
    const { data, loading, error } = useProcessPipelineQuery(documentId)
    const [open, setOpen] = useState<OpenPanel>(null)

    const handleValidated = async () => {
        setOpen(null)
        await queryClient.invalidateQueries({ queryKey: processKeys.all })
    }

    return (
        <div className="space-y-3 bg-zinc-50 px-4 py-4">
            {error ? <Alert tone="error">{error}</Alert> : null}
            {loading && !data ? <Alert>Carregando etapas do processo...</Alert> : null}
            {data ? (
                <ProcessBreakdown
                    pipeline={data}
                    onOpenLogs={() => setOpen('logs')}
                    onOpenValidation={() => setOpen('validation')}
                />
            ) : null}

            {open === 'logs' && data ? <IngestionLogsModal pipeline={data} onClose={() => setOpen(null)} /> : null}
            {open === 'validation' ? (
                <ValidationDrawer documentId={documentId} onClose={() => setOpen(null)} onValidated={handleValidated} />
            ) : null}
        </div>
    )
}
