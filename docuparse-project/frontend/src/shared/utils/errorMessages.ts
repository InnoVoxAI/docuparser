export interface ApiError {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- FR-010: único `any` documentado do arquivo.
    response?: { status?: number; data?: any }
    code?: string
    message?: string
}

export function asApiError(error: unknown): ApiError {
    return (error ?? {}) as ApiError
}

export function readError(error: unknown, fallback: string): string {
    const e = asApiError(error)
    const backendMessage = e.response?.data?.detail || e.response?.data?.error
    if (backendMessage) {
        return backendMessage
    }
    if (e.response?.status === 401) {
        return 'Sessao expirada ou nao autenticada. Faca login novamente.'
    }
    if (e.code === 'ERR_NETWORK' || e.message === 'Network Error') {
        return `${fallback} Verifique se backend-core e backend-com estao rodando.`
    }
    return fallback
}
