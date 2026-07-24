import React from 'react'
import type { Document, SchemaExample, SchemaField } from '../../types'
import { PROMPT_HINTS, type ReferenceReview, type SchemaForm } from './types'

// Helpers puros do builder LangExtract — movidos tal-e-qual de `src/main.tsx`.

export function buildLangExtractDefinition({
    schemaForm,
    fields,
    prompt,
    examples,
    normalizationRules,
    referenceReview,
    referenceDocument,
}: {
    schemaForm: SchemaForm
    fields: SchemaField[]
    prompt: string
    examples: SchemaExample[]
    normalizationRules: string
    referenceReview: ReferenceReview
    referenceDocument: Document | null
}) {
    let parsedRules = {}
    try {
        parsedRules = JSON.parse(normalizationRules || '{}')
    } catch {
        parsedRules = { parse_error: 'Regras JSON invalidas no momento da geracao.' }
    }

    return {
        kind: 'langextract_template',
        model_name: schemaForm.model_name,
        document_type: schemaForm.document_type,
        status: schemaForm.status,
        fields: fields
            .filter((field) => field.name.trim())
            .map((field) => ({
                name: field.name.trim(),
                type: field.type,
                required: Boolean(field.required),
                rule: field.rule,
            })),
        prompt: {
            instructions: prompt,
            guardrails: PROMPT_HINTS,
        },
        examples: examples.filter(
            (example) => example.field.trim() || example.expected.trim() || example.source.trim(),
        ),
        reference_review: {
            document_id: referenceDocument?.id || '',
            filename: referenceDocument?.original_filename || '',
            ocr_quality: referenceReview.quality,
            recommended_action: referenceReview.action,
            notes: referenceReview.notes,
        },
        post_processing: parsedRules,
        traceability: {
            require_source_span: true,
            allow_visual_validation: true,
        },
    }
}

export function buildLangExtractPreview(text: string, fields: SchemaField[]): string {
    const output: Record<string, unknown> = {}
    fields.forEach((field) => {
        if (!field.name) {
            return
        }
        const source = findLikelySourceLine(text, field.name)
        output[field.name] = {
            value: null,
            source,
            confidence: source ? 0.5 : 0,
            status: source ? 'candidate' : 'missing',
        }
    })
    return JSON.stringify(output, null, 2)
}

export function findLikelySourceLine(text: string, fieldName: string): string {
    if (!text || !fieldName) {
        return ''
    }
    const normalizedField = normalizeSearchText(fieldName).replaceAll('_', ' ')
    return text.split(/\r?\n/).find((line) => normalizeSearchText(line).includes(normalizedField)) || ''
}

export function renderHighlightedText(text: string, highlights: string[]): React.ReactNode {
    const terms = [...new Set(highlights.map((term) => term.trim()).filter((term) => term.length > 2))]
    if (terms.length === 0) {
        return text
    }

    const pattern = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'gi')
    return text.split(pattern).map((part, index) => {
        const isHighlighted = terms.some((term) => normalizeSearchText(term) === normalizeSearchText(part))
        return isHighlighted ? (
            <mark key={`${part}-${index}`} className="rounded bg-amber-100 px-0.5 text-amber-950">
                {part}
            </mark>
        ) : (
            <React.Fragment key={`${part}-${index}`}>{part}</React.Fragment>
        )
    })
}

export function normalizeSearchText(value: unknown): string {
    return String(value || '')
        .trim()
        .toLowerCase()
}

export function escapeRegExp(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
