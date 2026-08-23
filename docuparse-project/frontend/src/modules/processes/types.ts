import type { Paginated } from '../../types'

export type { Paginated }

/** Linha enxuta da sidebar — o detalhe completo vem de ProcessPipeline. */
export interface ProcessSummary {
    id: string
    original_filename: string
    channel: string
    status: string
    received_at: string
    has_error: boolean
}

export interface ProcessListParams {
    page: number
    page_size: number
    status?: string
    search?: string
}

export type StepExecutionStatus = 'OK' | 'ERROR'
export type StepStatus = StepExecutionStatus | 'PENDING'

export interface StepExecution {
    task_id: string
    attempt: number
    status: StepExecutionStatus
    duration_ms: number
    error_type: string | null
    error_message: string | null
    created_at: string
}

export type StepKey = 'register' | 'ocr' | 'extraction' | 'validation_decision'

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
