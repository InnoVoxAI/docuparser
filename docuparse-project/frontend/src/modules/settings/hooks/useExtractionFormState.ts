import { useState } from 'react'
import type { Document, SchemaExample } from '../../../types'
import { DEFAULT_LANGEXTRACT_FIELDS } from '../../../models/recibo/schemas'
import { DEFAULT_LANGEXTRACT_PROMPT } from '../../../models/recibo/prompts'
import type { LayoutForm, ReferenceReview, SchemaForm } from '../types'

/**
 * Só as declarações `useState` da área "Extração" (main.tsx ~1028-1066),
 * agrupadas em um hook próprio para `useExtractionState` caber no limite de
 * 150 linhas/arquivo (FR-012). Valores/setters iniciais idênticos ao
 * original.
 */
export function useExtractionFormState() {
    const [activeTab, setActiveTab] = useState('setup')
    const [schemaForm, setSchemaForm] = useState<SchemaForm>({
        schema_id: 'recibo_servico',
        version: 'v1',
        model_name: 'Recibo de servico',
        document_type: 'scanned_image',
        status: 'draft',
    })
    const [layoutForm, setLayoutForm] = useState<LayoutForm>({
        layout: 'recibo',
        document_type: 'scanned_image',
        schema_config_id: '',
        confidence_threshold: '0.75',
    })
    const [fields, setFields] = useState(DEFAULT_LANGEXTRACT_FIELDS)
    const [prompt, setPrompt] = useState(DEFAULT_LANGEXTRACT_PROMPT)
    const [normalizationRules, setNormalizationRules] = useState(
        '{\n  "valor_total": { "type": "decimal", "required": true, "min": 0 },\n  "fornecedor_cnpj": { "type": "cnpj", "validate_checksum": true }\n}',
    )
    const [examples, setExamples] = useState<SchemaExample[]>([
        { field: 'valor_total', expected: '120.00', source: 'Valor: 120,00' },
    ])
    const [referenceReview, setReferenceReview] = useState<ReferenceReview>({
        quality: 'pending',
        action: 'review_before_examples',
        notes: '',
    })
    const [selectedDocumentId, setSelectedDocumentId] = useState('')
    const [referenceDocument, setReferenceDocument] = useState<Document | null>(null)
    const [testOutput, setTestOutput] = useState('{}')
    const [selectedSchemaId, setSelectedSchemaId] = useState('')
    const [schemaSelectionSource, setSchemaSelectionSource] = useState('auto')
    const [message, setMessage] = useState('')

    return {
        activeTab,
        setActiveTab,
        schemaForm,
        setSchemaForm,
        layoutForm,
        setLayoutForm,
        fields,
        setFields,
        prompt,
        setPrompt,
        normalizationRules,
        setNormalizationRules,
        examples,
        setExamples,
        referenceReview,
        setReferenceReview,
        selectedDocumentId,
        setSelectedDocumentId,
        referenceDocument,
        setReferenceDocument,
        testOutput,
        setTestOutput,
        selectedSchemaId,
        setSelectedSchemaId,
        schemaSelectionSource,
        setSchemaSelectionSource,
        message,
        setMessage,
    }
}
