import { api } from '../../shared/lib/http'
import type { ExtractionResult } from './types'

// Resultado do polling de uma extração assíncrona (ver pollDocumentExtraction).
type ExtractionPollOutcome =
    { status: 'completed'; extraction: ExtractionResult } | { status: 'failed'; error: string } | { status: 'timeout' }

// Poll do detalhe do documento até que seu extraction_result mude — i.e. uma
// extração LLM em background terminou. O backend agora processa a extração de
// forma assíncrona (a chamada inline estourava o timeout do gateway em produção,
// aparecendo como 502/CORS). Retorna o novo extraction_result, uma falha
// registrada em metadata.extraction, ou timeout.
export async function pollDocumentExtraction(
    documentId: string,
    baseline: { resultUpdatedAt: string | null; metaUpdatedAt: string | null },
    { attempts = 40, intervalMs = 2500 }: { attempts?: number; intervalMs?: number } = {},
): Promise<ExtractionPollOutcome> {
    for (let i = 0; i < attempts; i++) {
        await new Promise((resolve) => setTimeout(resolve, intervalMs))
        try {
            const { data } = await api.get<{
                extraction_result?: ExtractionResult
                metadata?: { extraction?: { state?: string; updated_at?: string; error?: string } }
            }>(`/documents/${documentId}`)
            const extraction = data?.extraction_result
            if (extraction?.updated_at && extraction.updated_at !== baseline.resultUpdatedAt) {
                return { status: 'completed', extraction }
            }
            // Surface a real backend failure (e.g. langextract-service unreachable) instead
            // of polling forever — see document.metadata.extraction recorded by the backend.
            const meta = data?.metadata?.extraction
            if (meta?.state === 'failed' && meta.updated_at !== baseline.metaUpdatedAt) {
                return { status: 'failed', error: meta.error || 'Erro desconhecido na extracao.' }
            }
        } catch {
            /* transient error — keep polling */
        }
    }
    return { status: 'timeout' }
}

export function parseFieldEntry(raw: unknown): { value: string; confidence: number | null } {
    if (raw === null || raw === undefined) return { value: '', confidence: null }
    if (typeof raw === 'object' && 'value' in raw) {
        const obj = raw as { value?: unknown; confidence?: unknown }
        return {
            value: obj.value !== null && obj.value !== undefined ? String(obj.value) : '',
            confidence: typeof obj.confidence === 'number' ? obj.confidence : null,
        }
    }
    if (typeof raw === 'string') {
        try {
            const parsed = JSON.parse(raw)
            if (parsed && typeof parsed === 'object' && 'value' in parsed) {
                return {
                    value: parsed.value !== null && parsed.value !== undefined ? String(parsed.value) : '',
                    confidence: typeof parsed.confidence === 'number' ? parsed.confidence : null,
                }
            }
        } catch {
            // raw não é JSON válido; cai no fallback de string abaixo.
        }
    }
    return { value: String(raw), confidence: null }
}
