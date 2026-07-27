import type { SchemaConfig, SchemaExample, SchemaField } from '../../../types'
import type { SchemaForm } from '../types'
import {
    BOLETO_DEFAULT_SCHEMA_ID,
    BOLETO_DEFAULT_MODEL_NAME,
    BOLETO_DEFAULT_FIELDS,
} from '../../../models/boleto/schemas'
import { boletoPromptForDocumentType } from '../../../models/boleto/prompts'
import { BOLETO_DEFAULT_EXAMPLES } from '../../../models/boleto/examples'
import { BOLETO_DEFAULT_RULES } from '../../../models/boleto/rules'
import {
    NOTA_FISCAL_DEFAULT_SCHEMA_ID,
    NOTA_FISCAL_DEFAULT_MODEL_NAME,
    NOTA_FISCAL_DEFAULT_FIELDS,
} from '../../../models/nota_fiscal/schemas'
import { notaFiscalPromptForDocumentType } from '../../../models/nota_fiscal/prompts'
import { NOTA_FISCAL_DEFAULT_EXAMPLES } from '../../../models/nota_fiscal/examples'
import { NOTA_FISCAL_DEFAULT_RULES } from '../../../models/nota_fiscal/rules'
import {
    CONTA_AGUA_DEFAULT_SCHEMA_ID,
    CONTA_AGUA_DEFAULT_MODEL_NAME,
    CONTA_AGUA_DEFAULT_FIELDS,
} from '../../../models/contadeagua/schemas'
import { contaAguaPromptForDocumentType } from '../../../models/contadeagua/prompts'
import { CONTA_AGUA_DEFAULT_EXAMPLES } from '../../../models/contadeagua/examples'
import { CONTA_AGUA_DEFAULT_RULES } from '../../../models/contadeagua/rules'
import { DEFAULT_SCHEMA_ID, DEFAULT_MODEL_NAME, DEFAULT_LANGEXTRACT_FIELDS } from '../../../models/recibo/schemas'
import { DEFAULT_LANGEXTRACT_PROMPT } from '../../../models/recibo/prompts'

export { BOLETO_DEFAULT_SCHEMA_ID, NOTA_FISCAL_DEFAULT_SCHEMA_ID, CONTA_AGUA_DEFAULT_SCHEMA_ID }

/**
 * Aplicação por-tipo do resultado de `/classify-text` — extraído do efeito de
 * auto-classificação original (main.tsx ~1150-1270) em funções puras, uma por
 * tipo de documento default (boleto/nota_fiscal/conta_agua), para caber sob o
 * limite de 150 linhas/arquivo (FR-012). Cada função replica exatamente os
 * dois ramos do original: schema já existe no backend (`loadExistingSchema`
 * + sobrescrita pelos DEFAULT_* hardcoded, igual ao código original — essa
 * sobreposição parcial já existia, não é um bug introduzido aqui) vs. schema
 * ainda não existe (usa só os DEFAULT_* locais).
 */
export interface ClassificationSetters {
    setFields: (fields: SchemaField[]) => void
    setExamples: (examples: SchemaExample[]) => void
    setNormalizationRules: (rules: string) => void
    setSchemaForm: (updater: (current: SchemaForm) => SchemaForm) => void
    setPrompt: (prompt: string) => void
    setSelectedSchemaId: (id: string) => void
    loadExistingSchema: (schemaId: string, options?: { source?: string }) => void
}

export function applyNotaFiscal(docType: string, matchedSchema: SchemaConfig | undefined, s: ClassificationSetters) {
    const notaPrompt = notaFiscalPromptForDocumentType(docType)
    if (matchedSchema) {
        s.loadExistingSchema(matchedSchema.id, { source: 'auto' })
    } else {
        s.setSelectedSchemaId('')
    }
    s.setSchemaForm((current) => ({
        ...current,
        model_name: NOTA_FISCAL_DEFAULT_MODEL_NAME,
        schema_id: NOTA_FISCAL_DEFAULT_SCHEMA_ID,
        document_type: docType,
    }))
    s.setFields(NOTA_FISCAL_DEFAULT_FIELDS)
    s.setPrompt(notaPrompt)
    s.setExamples(NOTA_FISCAL_DEFAULT_EXAMPLES)
    s.setNormalizationRules(JSON.stringify(NOTA_FISCAL_DEFAULT_RULES, null, 2))
}

export function applyContaAgua(docType: string, matchedSchema: SchemaConfig | undefined, s: ClassificationSetters) {
    const aguaPrompt = contaAguaPromptForDocumentType(docType)
    if (matchedSchema) {
        s.loadExistingSchema(matchedSchema.id, { source: 'auto' })
    } else {
        s.setSelectedSchemaId('')
    }
    s.setSchemaForm((current) => ({
        ...current,
        model_name: CONTA_AGUA_DEFAULT_MODEL_NAME,
        schema_id: CONTA_AGUA_DEFAULT_SCHEMA_ID,
        document_type: docType,
    }))
    s.setFields(CONTA_AGUA_DEFAULT_FIELDS)
    s.setPrompt(aguaPrompt)
    s.setExamples(CONTA_AGUA_DEFAULT_EXAMPLES)
    s.setNormalizationRules(JSON.stringify(CONTA_AGUA_DEFAULT_RULES, null, 2))
}

export function applyBoleto(docType: string, matchedSchema: SchemaConfig | undefined, s: ClassificationSetters) {
    const boletoPrompt = boletoPromptForDocumentType(docType)
    if (matchedSchema) {
        s.loadExistingSchema(matchedSchema.id, { source: 'auto' })
    } else {
        s.setSelectedSchemaId('')
    }
    s.setSchemaForm((current) => ({
        ...current,
        model_name: BOLETO_DEFAULT_MODEL_NAME,
        schema_id: BOLETO_DEFAULT_SCHEMA_ID,
        document_type: docType,
    }))
    s.setFields(BOLETO_DEFAULT_FIELDS)
    s.setPrompt(boletoPrompt)
    s.setExamples(BOLETO_DEFAULT_EXAMPLES)
    s.setNormalizationRules(JSON.stringify(BOLETO_DEFAULT_RULES, null, 2))
}

export function resetToDefaultSchema(
    s: Pick<ClassificationSetters, 'setSelectedSchemaId' | 'setSchemaForm' | 'setFields' | 'setPrompt' | 'setExamples'>,
) {
    s.setSelectedSchemaId('')
    s.setSchemaForm((current) => ({ ...current, model_name: DEFAULT_MODEL_NAME, schema_id: DEFAULT_SCHEMA_ID }))
    s.setFields(DEFAULT_LANGEXTRACT_FIELDS)
    s.setPrompt(DEFAULT_LANGEXTRACT_PROMPT)
    s.setExamples([])
}
