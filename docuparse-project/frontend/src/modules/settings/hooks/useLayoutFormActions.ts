import { readError } from '../../../shared/utils'
import { useAuth } from '../../auth'
import type { SchemaExample, SchemaField } from '../../../types'
import { DEFAULT_LANGEXTRACT_FIELDS } from '../../../models/recibo/schemas'
import { DEFAULT_LANGEXTRACT_PROMPT } from '../../../models/recibo/prompts'
import type { LayoutForm, ReferenceReview, SchemaForm } from '../types'
import type { CreateLayoutInput } from './useLayoutMutations'

interface Params {
    layoutForm: LayoutForm
    setLayoutForm: (updater: (current: LayoutForm) => LayoutForm) => void
    setSchemaForm: (updater: (current: SchemaForm) => SchemaForm) => void
    setFields: (fields: SchemaField[]) => void
    setPrompt: (prompt: string) => void
    setExamples: (examples: SchemaExample[]) => void
    setReferenceReview: (review: ReferenceReview) => void
    setSelectedSchemaId: (id: string) => void
    setMessage: (message: string) => void
    createLayoutMutation: (input: CreateLayoutInput) => Promise<unknown>
}

/**
 * `createLayout` (main.tsx ~1517-1533) e `startNewModel` (o handler inline
 * do botão "Novo modelo", main.tsx ~1697-1720) — separados de
 * `useSchemaFormActions` só para caber no limite de 150 linhas/arquivo
 * (FR-012).
 */
export function useLayoutFormActions(params: Params) {
    const { currentTenant } = useAuth()
    const {
        layoutForm,
        setLayoutForm,
        setSchemaForm,
        setFields,
        setPrompt,
        setExamples,
        setReferenceReview,
        setSelectedSchemaId,
        setMessage,
        createLayoutMutation,
    } = params

    async function createLayout() {
        setMessage('')
        try {
            await createLayoutMutation({
                tenant_slug: currentTenant ?? '',
                layout: layoutForm.layout,
                document_type: layoutForm.document_type,
                schema_config_id: layoutForm.schema_config_id,
                confidence_threshold: Number(layoutForm.confidence_threshold),
            })
            setLayoutForm((current) => ({ ...current, layout: '' }))
            setMessage('Layout criado.')
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao criar layout.'))
        }
    }

    function startNewModel() {
        setSelectedSchemaId('')
        setSchemaForm(() => ({
            schema_id: 'novo_modelo',
            version: 'v1',
            model_name: 'Novo modelo',
            document_type: 'scanned_image',
            status: 'draft',
        }))
        setLayoutForm(() => ({
            layout: 'novo_layout',
            document_type: 'scanned_image',
            schema_config_id: '',
            confidence_threshold: '0.75',
        }))
        setFields(DEFAULT_LANGEXTRACT_FIELDS)
        setPrompt(DEFAULT_LANGEXTRACT_PROMPT)
        setExamples([])
        setReferenceReview({ quality: 'pending', action: 'review_before_examples', notes: '' })
    }

    return { createLayout, startNewModel }
}
