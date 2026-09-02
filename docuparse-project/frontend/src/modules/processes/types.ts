import type { Paginated } from '../../types'

export type { Paginated }

// "classification" é a última caixa do diagrama (acontece depois da validação
// humana e segue fora da plataforma) — estática, como "register".
export type StepKey = 'register' | 'ocr' | 'extraction' | 'validation_decision' | 'classification'

/**
 * Status "de negócio" — os 4 rótulos que a coluna Status da Visão Geral de
 * Processos mostra, no lugar dos ~11 valores técnicos de `Document.status`.
 * Espelha `STATUS_GROUP_LABELS` do backend (`services/process_dashboard.py`).
 */
export type ProcessStatusGroup = 'em_fila' | 'aguardando_validacao' | 'aguardando_classificacao' | 'erro'

export const STATUS_GROUP_LABELS: Record<ProcessStatusGroup, string> = {
    em_fila: 'Em Fila',
    aguardando_validacao: 'Aguardando validação',
    aguardando_classificacao: 'Aguardando classificação',
    erro: 'Erro',
}

/** Ordem dos chips de filtro no topo da tabela. */
export const STATUS_GROUP_ORDER: ProcessStatusGroup[] = [
    'em_fila',
    'aguardando_validacao',
    'aguardando_classificacao',
    'erro',
]

/** Linha da tabela da Visão Geral — o detalhe (breakdown) vem de ProcessPipeline. */
export interface ProcessSummary {
    id: string
    original_filename: string
    channel: string
    status: string
    /** Rótulo "de negócio" pré-calculado pelo backend (ver ProcessStatusGroup). */
    status_label: string
    received_at: string
    has_error: boolean
    current_stage: StepKey
}

export interface ProcessListParams {
    page: number
    page_size: number
    search?: string
    /** CSV de ProcessStatusGroup (chips são multi-seleção). */
    status_group?: string
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
    /** Saída da tentativa (schema/confiança/campos extraídos, decisão+motivo
     * da validação, etc.) — shape varia por step, já vem redigida do backend. */
    payload: Record<string, unknown>
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
