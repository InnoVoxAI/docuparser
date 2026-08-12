import { useEffect } from 'react'
import { boletoPromptForDocumentType } from '../../../models/boleto/prompts'
import { BOLETO_DEFAULT_SCHEMA_ID } from '../../../models/boleto/schemas'
import { notaFiscalPromptForDocumentType } from '../../../models/nota_fiscal/prompts'
import { NOTA_FISCAL_DEFAULT_SCHEMA_ID } from '../../../models/nota_fiscal/schemas'
import { contaAguaPromptForDocumentType } from '../../../models/contadeagua/prompts'
import { CONTA_AGUA_DEFAULT_SCHEMA_ID } from '../../../models/contadeagua/schemas'
import type { SchemaForm } from '../types'

/**
 * Os 3 efeitos "manter o prompt alinhado ao tipo de documento detectado"
 * (main.tsx ~1284-1315), extraídos tal-e-qual. `prompt` intencionalmente fora
 * dos arrays de deps — mesmo aviso `exhaustive-deps` pré-existente desde
 * T004, apenas relocado (ver Resultado T036-T040).
 */
export function usePromptSyncEffects(schemaForm: SchemaForm, prompt: string, setPrompt: (value: string) => void) {
    useEffect(() => {
        if (schemaForm.schema_id !== BOLETO_DEFAULT_SCHEMA_ID) return
        const boletoPrompt = boletoPromptForDocumentType(schemaForm.document_type)
        if (prompt !== boletoPrompt) setPrompt(boletoPrompt)
    }, [schemaForm.schema_id, schemaForm.document_type])

    useEffect(() => {
        if (schemaForm.schema_id !== NOTA_FISCAL_DEFAULT_SCHEMA_ID) return
        const notaPrompt = notaFiscalPromptForDocumentType(schemaForm.document_type)
        if (prompt !== notaPrompt) setPrompt(notaPrompt)
    }, [schemaForm.schema_id, schemaForm.document_type])

    useEffect(() => {
        if (schemaForm.schema_id !== CONTA_AGUA_DEFAULT_SCHEMA_ID) return
        const aguaPrompt = contaAguaPromptForDocumentType(schemaForm.document_type)
        if (prompt !== aguaPrompt) setPrompt(aguaPrompt)
    }, [schemaForm.schema_id, schemaForm.document_type])
}
