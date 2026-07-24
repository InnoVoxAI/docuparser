import { useState } from 'react'
import { useLayoutsQuery } from '../hooks/useLayoutsQuery'
import { useSchemasQuery } from '../hooks/useSchemasQuery'
import { useWhatsAppPoll } from '../hooks/useWhatsAppPoll'
import { SETTINGS_AREAS } from '../types'
import { EmailSettingsPanel } from './EmailSettingsPanel'
import { ExtractionPanel } from './ExtractionPanel'
import { IntegrationSettingsPanel } from './IntegrationSettingsPanel'
import { OcrSettingsPanel } from './OcrSettingsPanel'
import { WhatsAppSettingsPanel } from './WhatsAppSettingsPanel'

/**
 * Container de Configurações — só a alternância de área (`SETTINGS_AREAS`)
 * permanece aqui; cada área agora é auto-contida (busca/salva os próprios
 * dados), sem `schemas`/`layouts`/`onChanged` vindos de fora (ver T039 —
 * `schemas`/`layouts` saíram de `AppOutletContext`).
 */
export function SettingsView() {
    const [activeSettingsArea, setActiveSettingsArea] = useState('extraction')
    const { data: schemas } = useSchemasQuery()
    const { data: layouts } = useLayoutsQuery()
    const { message: whatsappMessage, pollWhatsApp } = useWhatsAppPoll()

    return (
        <div className="space-y-4">
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="flex gap-1 overflow-x-auto border-b border-zinc-200 px-3 py-2">
                    {SETTINGS_AREAS.map((area) => (
                        <button
                            key={area.id}
                            type="button"
                            onClick={() => setActiveSettingsArea(area.id)}
                            className={`h-9 shrink-0 rounded-md px-3 text-sm font-medium ${activeSettingsArea === area.id ? 'bg-zinc-900 text-white' : 'text-zinc-600 hover:bg-zinc-100'}`}
                        >
                            {area.label}
                        </button>
                    ))}
                </div>
                {activeSettingsArea === 'extraction' ? <ExtractionPanel schemas={schemas} layouts={layouts} /> : null}
                {activeSettingsArea === 'ocr-routing' ? <OcrSettingsPanel /> : null}
                {activeSettingsArea === 'email' ? <EmailSettingsPanel /> : null}
                {activeSettingsArea === 'whatsapp' ? (
                    <WhatsAppSettingsPanel onPoll={pollWhatsApp} message={whatsappMessage} />
                ) : null}
                {activeSettingsArea === 'integrations' ? <IntegrationSettingsPanel /> : null}
            </section>
        </div>
    )
}
