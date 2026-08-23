import { useState } from 'react'
import { useOutletContext } from 'react-router'
import { Alert, EmptyState } from '../../../shared/components'
import { Workflow } from 'lucide-react'
import type { AppOutletContext } from '../../../types'
import { useProcessPipelineQuery } from '../hooks/useProcessPipelineQuery'
import { useProcessesQuery } from '../hooks/useProcessesQuery'
import { useRetryStepMutation } from '../hooks/useRetryStepMutation'
import type { StepKey } from '../types'
import { ProcessPipelineDiagram } from './ProcessPipelineDiagram'
import { ProcessesSidebar } from './ProcessesSidebar'
import { StepDetailPanel } from './StepDetailPanel'

export function ProcessesView() {
    const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)
    const [selectedStepKey, setSelectedStepKey] = useState<StepKey | null>(null)
    // Módulo `processes` é uma rota irmã de `documents` sob o mesmo AppLayout
    // (mesma dependência cruzada documentada em ValidationRoute.tsx) — reusa
    // `navigateToValidation` em vez de duplicar a lógica de seleção+navegação.
    const { navigateToValidation } = useOutletContext<AppOutletContext>()

    const processesQuery = useProcessesQuery()
    const pipelineQuery = useProcessPipelineQuery(selectedDocumentId)
    const { retryStep, retrying, retryError } = useRetryStepMutation()

    const selectDocument = (id: string) => {
        setSelectedDocumentId(id)
        setSelectedStepKey(null)
    }

    const selectedStep = pipelineQuery.data?.steps.find((step) => step.key === selectedStepKey) ?? null

    const handleRetry = async () => {
        if (!selectedDocumentId || !selectedStepKey) return
        await retryStep({ documentId: selectedDocumentId, step: selectedStepKey })
    }

    return (
        <div className="grid h-full grid-cols-[280px_1fr] overflow-hidden rounded-md border border-zinc-200">
            <ProcessesSidebar
                data={processesQuery.data}
                loading={processesQuery.loading}
                error={processesQuery.error}
                search={processesQuery.search}
                onSearchChange={processesQuery.setSearch}
                selectedId={selectedDocumentId}
                onSelect={selectDocument}
                onPageChange={processesQuery.setPage}
            />
            <div className="flex flex-col overflow-y-auto bg-zinc-50">
                {!selectedDocumentId ? (
                    <EmptyState icon={Workflow} text="Selecione um processo na lista pra ver o pipeline." />
                ) : (
                    <>
                        {pipelineQuery.error ? <Alert tone="error">{pipelineQuery.error}</Alert> : null}
                        {pipelineQuery.loading ? <Alert>Carregando pipeline...</Alert> : null}
                        {pipelineQuery.data ? (
                            <>
                                <div className="border-b border-zinc-200 bg-white px-6 py-3">
                                    <h2 className="text-sm font-medium text-zinc-700">
                                        {pipelineQuery.data.original_filename}
                                    </h2>
                                </div>
                                <div className="px-6">
                                    <ProcessPipelineDiagram
                                        steps={pipelineQuery.data.steps}
                                        selectedStepKey={selectedStepKey}
                                        onSelectStep={setSelectedStepKey}
                                    />
                                </div>
                                <div className="flex-1 border-t border-zinc-200 bg-white px-2">
                                    <StepDetailPanel
                                        step={selectedStep}
                                        onRetry={handleRetry}
                                        retrying={retrying}
                                        retryError={retryError}
                                        onGoToValidation={() => navigateToValidation(selectedDocumentId)}
                                    />
                                </div>
                            </>
                        ) : null}
                    </>
                )}
            </div>
        </div>
    )
}
