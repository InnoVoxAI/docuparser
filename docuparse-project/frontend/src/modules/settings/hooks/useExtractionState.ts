import { useMemo } from 'react'
import type { LayoutConfig, SchemaConfig } from '../../../types'
import { BOLETO_DEFAULT_SCHEMA_ID } from '../../../models/boleto/schemas'
import { NOTA_FISCAL_DEFAULT_SCHEMA_ID } from '../../../models/nota_fiscal/schemas'
import { CONTA_AGUA_DEFAULT_SCHEMA_ID } from '../../../models/contadeagua/schemas'
import { useSchemaMutations } from './useSchemaMutations'
import { useLayoutMutations } from './useLayoutMutations'
import { useAutoClassification } from './useAutoClassification'
import { usePromptSyncEffects } from './usePromptSyncEffects'
import { useReferenceDocumentLoader } from './useReferenceDocumentLoader'
import { useSchemaFormActions } from './useSchemaFormActions'
import { useLayoutFormActions } from './useLayoutFormActions'
import { useExtractionFormState } from './useExtractionFormState'
import { buildLangExtractDefinition } from '../utils'

/**
 * Estado/efeitos/handlers da área "Extração" (builder LangExtract) de
 * Configurações — extraído de `SettingsView` (main.tsx ~1018-1634) tal-e-qual
 * (fora de escopo de conversão RHF+Zod, ver decisão #8 do handoff de
 * T036-T040). Puramente o orquestrador: `useExtractionFormState` guarda os
 * `useState`, `useReferenceDocumentLoader`/`useAutoClassification`/
 * `usePromptSyncEffects` os 3 blocos de efeitos, `useSchemaFormActions` os
 * handlers de criar/salvar/publicar — cada um em arquivo próprio só para
 * caber no limite de 150 linhas/arquivo (FR-012).
 */
export function useExtractionState(schemas: SchemaConfig[], layouts: LayoutConfig[]) {
    const state = useExtractionFormState()
    const { schemaForm, layoutForm, fields, prompt, normalizationRules, examples, referenceReview, referenceDocument } =
        state

    const boletoSchema = useMemo(() => schemas.find((s) => s.schema_id === BOLETO_DEFAULT_SCHEMA_ID), [schemas])
    const notaFiscalSchema = useMemo(
        () => schemas.find((s) => s.schema_id === NOTA_FISCAL_DEFAULT_SCHEMA_ID),
        [schemas],
    )
    const contaAguaSchema = useMemo(() => schemas.find((s) => s.schema_id === CONTA_AGUA_DEFAULT_SCHEMA_ID), [schemas])

    const activeLayout = layouts.find(
        (layout: LayoutConfig) =>
            layout.schema_config_id === state.selectedSchemaId ||
            (layout.layout === layoutForm.layout && layout.document_type === layoutForm.document_type),
    )

    const schemaDefinition = useMemo(
        () =>
            buildLangExtractDefinition({
                schemaForm,
                fields,
                prompt,
                examples,
                normalizationRules,
                referenceReview,
                referenceDocument,
            }),
        [schemaForm, fields, prompt, examples, normalizationRules, referenceReview, referenceDocument],
    )

    const { saveSchema } = useSchemaMutations()
    const { createLayout: createLayoutMutation } = useLayoutMutations()

    const { loadExistingSchema, createSchema, saveDraft, goToNextStep } = useSchemaFormActions({
        schemas,
        layouts,
        schemaForm,
        setSchemaForm: state.setSchemaForm,
        setLayoutForm: state.setLayoutForm,
        setFields: state.setFields,
        setPrompt: state.setPrompt,
        setExamples: state.setExamples,
        setNormalizationRules: state.setNormalizationRules,
        setReferenceReview: state.setReferenceReview,
        setSelectedSchemaId: state.setSelectedSchemaId,
        setSchemaSelectionSource: state.setSchemaSelectionSource,
        setMessage: state.setMessage,
        activeTab: state.activeTab,
        setActiveTab: state.setActiveTab,
        selectedSchemaId: state.selectedSchemaId,
        schemaDefinition,
        saveSchema,
    })

    const { createLayout, startNewModel } = useLayoutFormActions({
        layoutForm,
        setLayoutForm: state.setLayoutForm,
        setSchemaForm: state.setSchemaForm,
        setFields: state.setFields,
        setPrompt: state.setPrompt,
        setExamples: state.setExamples,
        setReferenceReview: state.setReferenceReview,
        setSelectedSchemaId: state.setSelectedSchemaId,
        setMessage: state.setMessage,
        createLayoutMutation,
    })

    useReferenceDocumentLoader(
        state.selectedDocumentId,
        fields,
        state.setSchemaSelectionSource,
        state.setReferenceDocument,
        state.setTestOutput,
        state.setSchemaForm,
        state.setLayoutForm,
        state.setMessage,
    )

    useAutoClassification(
        referenceDocument,
        state.schemaSelectionSource,
        schemaForm,
        { boleto: boletoSchema, notaFiscal: notaFiscalSchema, contaAgua: contaAguaSchema },
        {
            setFields: state.setFields,
            setExamples: state.setExamples,
            setNormalizationRules: state.setNormalizationRules,
            setSchemaForm: state.setSchemaForm,
            setPrompt: state.setPrompt,
            setSelectedSchemaId: state.setSelectedSchemaId,
            loadExistingSchema,
        },
    )

    usePromptSyncEffects(schemaForm, prompt, state.setPrompt)

    // `...state` inclui alguns campos que nenhum consumidor usa hoje
    // (`setReferenceDocument`, `schemaSelectionSource`, `setSchemaSelectionSource`)
    // — inofensivo (objeto de retorno maior, nenhum componente depende da forma
    // exata), e evita repetir aqui a lista inteira de campos já nomeados em
    // `useExtractionFormState`.
    return {
        ...state,
        activeLayout,
        schemaDefinition,
        loadExistingSchema,
        createSchema,
        saveDraft,
        goToNextStep,
        createLayout,
        startNewModel,
    }
}
