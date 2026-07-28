import { useEffect } from 'react'
import { api } from '../../../shared/lib/http'
import type { Document, SchemaConfig } from '../../../types'
import type { SchemaForm } from '../types'
import {
    applyBoleto,
    applyContaAgua,
    applyNotaFiscal,
    resetToDefaultSchema,
    BOLETO_DEFAULT_SCHEMA_ID,
    NOTA_FISCAL_DEFAULT_SCHEMA_ID,
    CONTA_AGUA_DEFAULT_SCHEMA_ID,
    type ClassificationSetters,
} from './applySchemaClassification'

/**
 * Efeito de auto-classificação (`POST /classify-text`) extraído de
 * `useExtractionState` — só a orquestração do fetch + despacho por tipo fica
 * aqui; a aplicação de cada tipo vive em `applySchemaClassification.ts`
 * (limite de 150 linhas/arquivo, FR-012). Comportamento idêntico ao efeito
 * original de `main.tsx` (~1150-1270).
 */
export function useAutoClassification(
    referenceDocument: Document | null,
    schemaSelectionSource: string,
    schemaForm: SchemaForm,
    matches: { boleto?: SchemaConfig; notaFiscal?: SchemaConfig; contaAgua?: SchemaConfig },
    setters: ClassificationSetters,
) {
    useEffect(() => {
        const rawText = referenceDocument?.full_transcription || ''
        if (!rawText || schemaSelectionSource === 'manual') return

        const capturedSchemaId = schemaForm.schema_id
        let ignore = false
        api.post<{ schema_id?: string }>('/classify-text', { text: rawText })
            .then((res) => {
                if (ignore) return
                const detectedType = res.data?.schema_id
                const docType = referenceDocument?.document_type || schemaForm.document_type

                if (detectedType === NOTA_FISCAL_DEFAULT_SCHEMA_ID) {
                    applyNotaFiscal(docType, matches.notaFiscal, setters)
                    return
                }
                if (detectedType === CONTA_AGUA_DEFAULT_SCHEMA_ID) {
                    applyContaAgua(docType, matches.contaAgua, setters)
                    return
                }
                if (detectedType === BOLETO_DEFAULT_SCHEMA_ID) {
                    applyBoleto(docType, matches.boleto, setters)
                    return
                }
                if (
                    [BOLETO_DEFAULT_SCHEMA_ID, NOTA_FISCAL_DEFAULT_SCHEMA_ID, CONTA_AGUA_DEFAULT_SCHEMA_ID].includes(
                        capturedSchemaId,
                    )
                ) {
                    resetToDefaultSchema(setters)
                }
            })
            .catch(() => {})
        return () => {
            ignore = true
        }
    }, [
        referenceDocument?.id,
        referenceDocument?.full_transcription,
        referenceDocument?.document_type,
        matches.boleto,
        matches.notaFiscal,
        matches.contaAgua,
        schemaSelectionSource,
    ])
}
