import { readError } from '../../../shared/utils'
import type { LayoutConfig, SchemaConfig, SchemaExample, SchemaField } from '../../../types'
import { SETTINGS_TABS, type LayoutForm, type ReferenceReview, type SchemaForm } from '../types'
import { loadExistingSchemaAction } from './loadExistingSchemaAction'
import type { SaveSchemaInput } from './useSchemaMutations'

interface Params {
    schemas: SchemaConfig[]
    layouts: LayoutConfig[]
    schemaForm: SchemaForm
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
    activeTab: string
    setActiveTab: (tab: string) => void
    selectedSchemaId: string
    schemaDefinition: unknown
    saveSchema: (input: SaveSchemaInput) => Promise<{ data: SchemaConfig }>
}

/**
 * Handlers de `loadExistingSchema`/`createSchema`/`saveDraft`/`goToNextStep`
 * (main.tsx ~1394-1515) — `createLayout`/`startNewModel` moram em
 * `useLayoutFormActions.ts` (arquivo irmão, ver comentário lá), e
 * `loadExistingSchema` delega para `loadExistingSchemaAction.ts` (função
 * pura). Split feito só para caber no limite de 150 linhas/arquivo
 * (FR-012). `createSchema`/`saveDraft` usam `useSchemaMutations` (invalida
 * `settingsKeys.all`) em vez do antigo `onChanged()` prop-callback (decisão
 * #7 do handoff de T036-T040).
 */
export function useSchemaFormActions(params: Params) {
    const {
        schemas,
        layouts,
        schemaForm,
        setSchemaForm,
        setLayoutForm,
        setFields,
        setPrompt,
        setExamples,
        setNormalizationRules,
        setReferenceReview,
        setSelectedSchemaId,
        setSchemaSelectionSource,
        setMessage,
        activeTab,
        setActiveTab,
        selectedSchemaId,
        schemaDefinition,
        saveSchema,
    } = params

    function loadExistingSchema(schemaId: string, options: { source?: string } = {}) {
        loadExistingSchemaAction(schemaId, options, {
            schemas,
            layouts,
            setSchemaForm,
            setLayoutForm,
            setFields,
            setPrompt,
            setExamples,
            setNormalizationRules,
            setReferenceReview,
            setSelectedSchemaId,
            setSchemaSelectionSource,
            setMessage,
        })
    }

    async function createSchema() {
        setMessage('')
        try {
            const response = await saveSchema({
                id: selectedSchemaId || undefined,
                schema_id: schemaForm.schema_id,
                version: schemaForm.version,
                definition: schemaDefinition as Record<string, unknown>,
                is_active: schemaForm.status !== 'disabled',
            })
            setSelectedSchemaId(response.data.id)
            setMessage('Modelo LangExtract salvo como schema.')
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao criar schema.'))
        }
    }

    async function saveDraft(): Promise<boolean> {
        setMessage('')
        try {
            const draftDefinition = { ...(schemaDefinition as Record<string, unknown>), status: 'draft' }
            const response = await saveSchema({
                id: selectedSchemaId || undefined,
                schema_id: schemaForm.schema_id,
                version: schemaForm.version,
                definition: draftDefinition,
                is_active: true,
            })
            setSelectedSchemaId(response.data.id)
            setSchemaForm((current) => ({ ...current, status: 'draft' }))
            setMessage('Rascunho salvo.')
            return true
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao salvar rascunho.'))
            return false
        }
    }

    async function goToNextStep() {
        const saved = await saveDraft()
        if (!saved) return
        const currentIndex = SETTINGS_TABS.findIndex((tab) => tab.id === activeTab)
        const nextTab = SETTINGS_TABS[currentIndex + 1]
        if (nextTab) setActiveTab(nextTab.id)
    }

    return { loadExistingSchema, createSchema, saveDraft, goToNextStep }
}
