import { engineLabel } from './EngineSelect'
import type { OcrSettingsFormValues } from '../schemas/ocrSettingsSchema'

export function OcrRoutingSummary({ settings }: { settings: OcrSettingsFormValues }) {
    const activeOcrRoutes = [
        {
            type: 'PDF textual',
            classification: 'digital_pdf',
            engine: engineLabel(settings.digital_pdf_engine),
            detail: 'Usado quando o classificador encontra blocos de texto suficientes no PDF.',
        },
        {
            type: 'Imagem/PDF escaneado',
            classification: 'scanned_image',
            engine: engineLabel(settings.scanned_image_engine),
            detail: 'Usado para documentos sem camada textual confiavel, incluindo fotos e PDFs imagem.',
        },
        {
            type: 'Manuscrito complexo',
            classification: 'handwritten_complex',
            engine: engineLabel(settings.handwritten_engine),
            detail: 'Usado para documentos com escrita manual ou baixa estrutura textual.',
        },
        {
            type: 'Fallback tecnico',
            classification: 'fallback',
            engine: engineLabel(settings.technical_fallback_engine),
            detail: 'Usado apenas quando o engine primario falha antes de retornar transcricao.',
        },
    ]

    return (
        <section className="rounded-md border border-zinc-200 p-4">
            <div className="mb-3 text-sm font-semibold">Roteamento ativo</div>
            <div className="space-y-3">
                {activeOcrRoutes.map((route) => (
                    <div key={route.classification} className="rounded-md border border-zinc-200 bg-zinc-50 p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                                <div className="text-sm font-semibold">{route.type}</div>
                                <div className="mt-1 text-xs text-zinc-500">{route.classification}</div>
                            </div>
                            <span className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs font-semibold text-zinc-700">
                                {route.engine}
                            </span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-zinc-600">{route.detail}</p>
                    </div>
                ))}
            </div>
        </section>
    )
}
