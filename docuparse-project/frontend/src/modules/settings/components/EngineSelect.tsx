export function EngineSelect({ value, onChange }: { value?: string; onChange: (value: string) => void }) {
    return (
        <select className="input" value={value || 'docling'} onChange={(event) => onChange(event.target.value)}>
            <option value="docling">Docling</option>
            <option value="openrouter">OpenRouter</option>
            <option value="tesseract">Tesseract</option>
        </select>
    )
}

export function engineLabel(value?: string): string {
    return (
        (
            {
                docling: 'Docling',
                openrouter: 'OpenRouter',
                tesseract: 'Tesseract',
            } as Record<string, string>
        )[value ?? ''] ||
        value ||
        '-'
    )
}
