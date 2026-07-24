// Os eventos/streams de DLQ têm forma dinâmica (payloads de workers diversos);
// campos ad-hoc são renderizados diretamente, por isso o índice permissivo.
export interface DlqEvent {
    id?: string
    original_stream?: string
    source?: string
    error_type?: string
    error?: string
    payload?: unknown
    occurred_at?: string | number | Date | null
    event_type?: string
    event_id?: string
    [key: string]: unknown
}

export interface DlqStream {
    stream: string
    count: number
    latest?: DlqEvent
    [key: string]: unknown
}

export interface DlqSummary {
    total: number
    streams: DlqStream[]
}
