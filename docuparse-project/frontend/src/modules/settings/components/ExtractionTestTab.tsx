import { Field } from '../../../shared/components'
import type { Document, SchemaExample, SchemaField } from '../../../types'
import { DocumentPreview } from './DocumentPreview'
import { HighlightedOcrText } from './HighlightedOcrText'

export function ExtractionTestTab({
    referenceDocument,
    fields,
    examples,
    testOutput,
    setTestOutput,
}: {
    referenceDocument: Document | null
    fields: SchemaField[]
    examples: SchemaExample[]
    testOutput: string
    setTestOutput: (value: string) => void
}) {
    return (
        <div className="grid gap-4 xl:grid-cols-[minmax(320px,0.9fr)_minmax(360px,1.1fr)_minmax(320px,0.8fr)]">
            <DocumentPreview document={referenceDocument} />
            <HighlightedOcrText
                text={referenceDocument?.full_transcription || ''}
                fields={fields}
                examples={examples}
            />
            <Field label="Preview JSON">
                <textarea
                    value={testOutput}
                    onChange={(event) => setTestOutput(event.target.value)}
                    className="input min-h-[520px] font-mono"
                />
            </Field>
        </div>
    )
}
