import { RefreshCw } from 'lucide-react'
import { Alert, Field } from '../../../shared/components'
import { ConfigIntro } from './ConfigIntro'

/**
 * T036/T037 pedem RHF+Zod "por aba", mas esta aba não tem nenhum estado de
 * formulário real hoje: todo input é não-controlado / só `defaultValue` /
 * `placeholder`, sem nenhum backend endpoint por trás — só o botão "Processar
 * arquivos do WhatsApp" (`onPoll`) faz algo de verdade. Inventar um schema
 * Zod/`useForm` aqui validaria campos que não são persistidos por nada,
 * então este painel foi movido tal-e-qual (puramente apresentacional),
 * conforme decisão #2 do handoff de T036-T040. `message` é só exibido — o
 * estado/fetch de `pollWhatsApp` vive em `useWhatsAppPoll` (chamado pelo
 * container `SettingsView`), este componente permanece sem estado próprio.
 */
export function WhatsAppSettingsPanel({
    onPoll,
    message,
}: {
    onPoll: () => void | Promise<unknown>
    message?: string
}) {
    return (
        <div className="space-y-4 p-4">
            {message ? <Alert>{message}</Alert> : null}
            <ConfigIntro
                title="WhatsApp"
                text="Configure a recepcao via Twilio WhatsApp. Enquanto as credenciais finais nao estiverem disponiveis, os testes reais podem falhar sem bloquear o restante do desenvolvimento."
            />
            <div className="flex flex-wrap justify-end gap-2">
                <button
                    type="button"
                    onClick={onPoll}
                    className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                >
                    <RefreshCw size={16} aria-hidden="true" />
                    Processar arquivos do WhatsApp
                </button>
            </div>
            <div className="grid gap-4 xl:grid-cols-2">
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Twilio</div>
                    <div className="grid gap-3 md:grid-cols-2">
                        <Field label="Account SID">
                            <input className="input" placeholder="AC..." />
                        </Field>
                        <Field label="Auth Token">
                            <input className="input" type="password" placeholder="secret" />
                        </Field>
                        <Field label="API Key SID">
                            <input className="input" placeholder="SK..." />
                        </Field>
                        <Field label="API Key Secret">
                            <input className="input" type="password" placeholder="secret" />
                        </Field>
                        <Field label="From Number">
                            <input className="input" placeholder="whatsapp:+14155238886" />
                        </Field>
                        <Field label="Numero de teste">
                            <input className="input" placeholder="whatsapp:+55..." />
                        </Field>
                    </div>
                </section>
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Webhook e midias</div>
                    <div className="grid gap-3">
                        <Field label="Webhook URL">
                            <input className="input" defaultValue="http://127.0.0.1:8070/api/v1/whatsapp/webhook" />
                        </Field>
                        <Field label="Validar assinatura Twilio">
                            <select className="input" defaultValue="enabled">
                                <option value="enabled">Sim</option>
                                <option value="disabled">Nao em dev local</option>
                            </select>
                        </Field>
                        <Field label="Tipos de midia aceitos">
                            <input
                                className="input"
                                defaultValue="application/pdf,image/jpeg,image/png,image/tiff,image/webp"
                            />
                        </Field>
                    </div>
                </section>
            </div>
        </div>
    )
}
