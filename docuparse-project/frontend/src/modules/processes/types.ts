import type { Paginated } from '../../types'

export type { Paginated }

export type StepKey = 'register' | 'ocr' | 'extraction' | 'validation_decision'
export type ProcessFilter = 'fail' | 'pending' | 'completed'

/** Linha enxuta da sidebar — o detalhe completo vem de ProcessPipeline. */
export interface ProcessSummary {
    id: string
    original_filename: string
    channel: string
    status: string
    received_at: string
    has_error: boolean
    current_stage: StepKey
}

export interface ProcessListParams {
    page: number
    page_size: number
    status?: string
    search?: string
    filter?: ProcessFilter
    stage?: StepKey
}

export type StepExecutionStatus = 'OK' | 'ERROR'
// 'REJECTED' só existe no nível do step (validation_decision quando o
// documento foi rejeitado) — a execução em si sempre foi bem-sucedida
// (StepExecutionStatus), o rejeitado é o resultado de negócio, não a task.
export type StepStatus = StepExecutionStatus | 'PENDING' | 'REJECTED'

export interface StepExecution {
    task_id: string
    attempt: number
    status: StepExecutionStatus
    duration_ms: number
    error_type: string | null
    error_message: string | null
    created_at: string
    /** Nome da orchestration_run dona desta execução (ex.: "document_processing",
     * "retry_ocr", "document_validation") — não exibido diretamente, só usado
     * como contexto; `triggered_by` já resume o que importa pro usuário. */
    run_name: string
    /** null = disparo automático (pipeline pós-upload); caso contrário, o
     * username de quem clicou "Tentar novamente" ou tomou a decisão. */
    triggered_by: string | null
}

export interface ProcessStep {
    key: StepKey
    label: string
    status: StepStatus
    retryable: boolean
    executions: StepExecution[]
}

export interface ProcessPipeline {
    document_id: string
    original_filename: string
    steps: ProcessStep[]
}

export interface RetryStepResult {
    status: 'ok' | 'error'
    error: { type: string; message: string } | null
}
