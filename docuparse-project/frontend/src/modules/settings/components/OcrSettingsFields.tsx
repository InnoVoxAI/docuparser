import { Controller, type Control, type FieldErrors, type UseFormRegister } from 'react-hook-form'
import { Field } from '../../../shared/components'
import { EngineSelect } from './EngineSelect'
import type { OcrSettingsFormValues } from '../schemas/ocrSettingsSchema'

export function OcrSettingsFields({
    register,
    control,
    errors,
}: {
    register: UseFormRegister<OcrSettingsFormValues>
    control: Control<OcrSettingsFormValues>
    errors: FieldErrors<OcrSettingsFormValues>
}) {
    return (
        <section className="rounded-md border border-zinc-200 p-4">
            <div className="mb-3 text-sm font-semibold">Configuracao em uso</div>
            <div className="grid gap-3 md:grid-cols-2">
                <Field label="PDF textual">
                    <Controller
                        name="digital_pdf_engine"
                        control={control}
                        render={({ field }) => <EngineSelect value={field.value} onChange={field.onChange} />}
                    />
                </Field>
                <Field label="Imagem/PDF escaneado">
                    <Controller
                        name="scanned_image_engine"
                        control={control}
                        render={({ field }) => <EngineSelect value={field.value} onChange={field.onChange} />}
                    />
                </Field>
                <Field label="Manuscrito complexo">
                    <Controller
                        name="handwritten_engine"
                        control={control}
                        render={({ field }) => <EngineSelect value={field.value} onChange={field.onChange} />}
                    />
                </Field>
                <Field label="Fallback tecnico">
                    <Controller
                        name="technical_fallback_engine"
                        control={control}
                        render={({ field }) => <EngineSelect value={field.value} onChange={field.onChange} />}
                    />
                </Field>
                <Field label="Modelo OpenRouter primario">
                    <input
                        className="input"
                        {...register('openrouter_model')}
                        placeholder="Vazio usa OPENROUTER_MODEL do .env"
                    />
                </Field>
                <Field label="Modelo OpenRouter secundario">
                    <input
                        className="input"
                        {...register('openrouter_fallback_model')}
                        placeholder="qwen/qwen2.5-vl-72b-instruct"
                    />
                </Field>
                <Field label="Timeout segundos">
                    <input
                        className="input"
                        type="number"
                        min="10"
                        max="600"
                        {...register('timeout_seconds', { valueAsNumber: true })}
                    />
                    {errors.timeout_seconds ? (
                        <p className="mt-1 text-xs text-red-600">Informe um valor entre 10 e 600.</p>
                    ) : null}
                </Field>
                <Field label="Fallback se texto vazio">
                    <Controller
                        name="retry_empty_text_enabled"
                        control={control}
                        render={({ field }) => (
                            <select
                                className="input"
                                value={field.value ? 'enabled' : 'disabled'}
                                onChange={(event) => field.onChange(event.target.value === 'enabled')}
                            >
                                <option value="enabled">Tentar segundo modelo</option>
                                <option value="disabled">Nao tentar</option>
                            </select>
                        )}
                    />
                </Field>
                <Field label="Minimo de blocos de texto PDF">
                    <input
                        className="input"
                        type="number"
                        min="1"
                        max="200"
                        {...register('digital_pdf_min_text_blocks', { valueAsNumber: true })}
                    />
                    {errors.digital_pdf_min_text_blocks ? (
                        <p className="mt-1 text-xs text-red-600">Informe um valor entre 1 e 200.</p>
                    ) : null}
                </Field>
            </div>
            <p className="mt-3 text-sm leading-6 text-zinc-500">
                A chave OpenRouter continua no `.env` e nao e gravada aqui. PaddleOCR, EasyOCR, TrOCR, LlamaParse e
                DeepSeek permanecem como codigo legado/opcional, mas nao fazem parte do setup operacional atual.
            </p>
        </section>
    )
}
