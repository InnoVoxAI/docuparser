import { Field } from '../../../shared/components'
import { HintPanel } from './HintPanel'

export function ExtractionRulesTab({
    normalizationRules,
    setNormalizationRules,
}: {
    normalizationRules: string
    setNormalizationRules: (value: string) => void
}) {
    return (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
            <Field label="Regras de pos-processamento JSON">
                <textarea
                    value={normalizationRules}
                    onChange={(event) => setNormalizationRules(event.target.value)}
                    className="input min-h-[300px] font-mono"
                />
            </Field>
            <HintPanel
                title="Regras recomendadas"
                items={[
                    'Normalizar moeda para decimal.',
                    'Normalizar datas para YYYY-MM-DD.',
                    'Validar CPF/CNPJ por checksum.',
                    'Comparar valor liquido com total quando houver.',
                ]}
            />
        </div>
    )
}
