// `payload` é o corpo original do evento que falhou em um worker — formato
// heterogêneo por natureza (varia por origem/worker), por isso `unknown`. Os
// demais campos são os únicos efetivamente lidos pela UI (DlqEventsTable/
// DlqEventDetail/DlqStreamSummary); nenhum consumidor lê chave dinâmica, então
// o índice permissivo do nível do evento/stream foi removido (T054).
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
}

export interface DlqStream {
    stream: string
    count: number
    latest?: DlqEvent
}

export interface DlqSummary {
    total: number
    streams: DlqStream[]
}
