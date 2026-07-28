import type { LayoutConfig, SchemaConfig, SchemaExample, SchemaField } from '../../../types'
import type { LayoutForm, ReferenceReview, SchemaForm } from '../types'

export interface LoadExistingSchemaSetters {
    schemas: SchemaConfig[]
    layouts: LayoutConfig[]
    setSchemaForm: (updater: (current: SchemaForm) => SchemaForm) => void
    setLayoutForm: (updater: (current: LayoutForm) => LayoutForm) => void
    setFields: (fields: SchemaField[]) => void
    setPrompt: (prompt: string) => void
    setExamples: (examples: SchemaExample[]) => void
    setNormalizationRules: (rules: string) => void
    setReferenceReview: (review: ReferenceReview) => void
    setSelectedSchemaId: (id: string) => void
    setSchemaSelectionSource: (source: string) => void
    setMessage: (message: string) => void
}

/**
 * `loadExistingSchema` (main.tsx ~1394-1454) — carrega um schema já salvo no
 * backend para dentro do formulário local. Função pura (não é hook, não
 * chama nenhum hook internamente) para caber no limite de 150
 * linhas/arquivo (FR-012) sem fragmentar `useSchemaFormActions` mais do que
 * o necessário.
 */
export function loadExistingSchemaAction(
    schemaId: string,
    { source = 'manual' }: { source?: string } = {},
    s: LoadExistingSchemaSetters,
) {
    s.setSchemaSelectionSource(source)
    s.setSelectedSchemaId(schemaId)
    const schema = s.schemas.find((item) => item.id === schemaId)
    if (!schema) return
    const definition = schema.definition || {}
    s.setSchemaForm((current) => ({
        ...current,
        schema_id: schema.schema_id ?? current.schema_id,
        version: schema.version ?? current.version,
        model_name: definition.model_name || schema.schema_id || current.model_name,
        document_type: definition.document_type || current.document_type,
        status: definition.status || current.status,
    }))
    const linkedLayout = s.layouts.find((layout) => layout.schema_config_id === schema.id)
    if (linkedLayout) {
        s.setLayoutForm((current) => ({
            ...current,
            layout: linkedLayout.layout ?? current.layout,
            document_type: linkedLayout.document_type ?? current.document_type,
            schema_config_id: schema.id,
            confidence_threshold: String(linkedLayout.confidence_threshold ?? current.confidence_threshold),
        }))
    } else {
        s.setLayoutForm((current) => ({
            ...current,
            schema_config_id: schema.id,
            document_type: definition.document_type || current.document_type,
        }))
    }
    if (Array.isArray(definition.fields)) {
        s.setFields(
            definition.fields.map((field: Partial<SchemaField>) => ({
                name: field.name || '',
                type: field.type || 'string',
                required: Boolean(field.required),
                rule: field.rule || '',
            })),
        )
    }
    if (definition.prompt?.instructions) s.setPrompt(definition.prompt.instructions)
    if (Array.isArray(definition.examples)) s.setExamples(definition.examples)
    if (definition.post_processing) s.setNormalizationRules(JSON.stringify(definition.post_processing, null, 2))
    if (definition.reference_review) {
        s.setReferenceReview({
            quality: definition.reference_review.ocr_quality || 'pending',
            action: definition.reference_review.recommended_action || 'review_before_examples',
            notes: definition.reference_review.notes || '',
        })
    }
    s.setMessage(`Schema carregado: ${schema.schema_id} ${schema.version}`)
}
