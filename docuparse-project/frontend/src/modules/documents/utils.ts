import { api } from '../../shared/lib/http'
import type { ExtractionResult, FieldRow, FieldsMap } from './types'

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

// Siglas que devem ficar maiúsculas ao invés de "Title Case" normal.
const FIELD_NAME_ACRONYMS = new Set(['cnpj', 'cpf', 'nf', 'nfe', 'cep', 'uf', 'ie', 'erp', 'id'])

/** Transforma a chave técnica de um campo extraído (ex.: "valor_total",
 * "cnpjFornecedor") num rótulo legível pra tela de Validação (ex.: "Valor
 * Total", "CNPJ Fornecedor") — a análise não deveria ver snake_case/camelCase. */
export function humanizeFieldName(name: string): string {
    const spaced = name
        .replace(/[_-]+/g, ' ')
        .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
        .trim()
    if (!spaced) return name
    return spaced
        .split(/\s+/)
        .map((word) =>
            FIELD_NAME_ACRONYMS.has(word.toLowerCase())
                ? word.toUpperCase()
                : word.charAt(0).toUpperCase() + word.slice(1).toLowerCase(),
        )
        .join(' ')
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

/** Converte `extraction_result.fields` (mapa bruto do backend) nas mesmas
 * `FieldRow[]` que a tela de Validação edita — usado tanto pra popular
 * `fieldRows` quanto, em `useFieldExtraction`, pra saber se o que está na
 * tela ainda bate com o que foi persistido (`hasUnsavedChanges`). */
export function deriveFieldRowsFromFields(fields: FieldsMap | null | undefined): FieldRow[] {
    if (!fields) return []
    return Object.entries(fields)
        .filter(([, value]) => value !== '' && value !== null && value !== undefined)
        .map(([name, raw]) => {
            const { value, confidence } = parseFieldEntry(raw)
            return { name, value, confidence }
        })
        .filter((row) => row.value !== '' && row.value.toLowerCase() !== 'valor não encontrado')
}
