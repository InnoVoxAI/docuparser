import { z } from 'zod'

/**
 * Espelha as restrições hoje aplicadas apenas via atributos HTML `min`/`max`
 * dos inputs numéricos de `OcrSettingsPanel` (não eram bloqueadas em JS antes
 * de T036/T037 — só a validação nativa do navegador em `<input type="number">`,
 * facilmente contornável). O `zodResolver` passa a impedir de fato o submit
 * fora da faixa, o que é uma pequena melhoria de comportamento, não uma
 * regressão: os limites em si (10–600s, 1–200 blocos) já existiam no markup
 * original, só não eram garantidos antes de chegar ao backend.
 */
export const ocrSettingsSchema = z.object({
    digital_pdf_engine: z.string(),
    scanned_image_engine: z.string(),
    handwritten_engine: z.string(),
    technical_fallback_engine: z.string(),
    openrouter_model: z.string(),
    openrouter_fallback_model: z.string(),
    timeout_seconds: z.number().min(10).max(600),
    retry_empty_text_enabled: z.boolean(),
    digital_pdf_min_text_blocks: z.number().min(1).max(200),
})

export type OcrSettingsFormValues = z.infer<typeof ocrSettingsSchema>

export const OCR_SETTINGS_DEFAULTS: OcrSettingsFormValues = {
    digital_pdf_engine: 'docling',
    scanned_image_engine: 'openrouter',
    handwritten_engine: 'openrouter',
    technical_fallback_engine: 'tesseract',
    openrouter_model: '',
    openrouter_fallback_model: 'qwen/qwen2.5-vl-72b-instruct',
    timeout_seconds: 120,
    retry_empty_text_enabled: true,
    digital_pdf_min_text_blocks: 5,
}
