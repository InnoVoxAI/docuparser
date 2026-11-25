import { useState } from 'react'
import { displayField, type FieldSpec } from '../documentFields'
import type { PaymentDocumentDetail } from '../schemas/payments'

/**
 * Campos do documento. Os que decidem o casamento aparecem sempre (mesmo "não lido");
 * os opcionais só quando foram lidos, e os não lidos ficam atrás de um botão, para o
 * arquivo original ter espaço na tela.
 */
export function FieldGrid({ specs, detail }: { specs: FieldSpec[]; detail: PaymentDocumentDetail | undefined }) {
    const [showUnread, setShowUnread] = useState(false)
    const rows = specs.map((spec) => ({ spec, value: displayField(detail, spec) }))
    const hidden = rows.filter((row) => !row.value && !row.spec.strong)
    const visible = rows.filter((row) => row.value || row.spec.strong || showUnread)
    return (
        <div className="space-y-2">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm xl:grid-cols-3">
                {visible.map(({ spec, value }) => (
                    <div key={spec.label} className={spec.wide ? 'col-span-2 xl:col-span-3' : undefined}>
                        <dt className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{spec.label}</dt>
                        <dd
                            className={`break-words ${spec.strong ? 'font-semibold text-zinc-900' : 'text-zinc-800'} ${
                                spec.format === 'code' ? 'font-mono text-xs' : ''
                            }`}
                        >
                            {value || <span className="text-zinc-400">não lido</span>}
                        </dd>
                    </div>
                ))}
            </dl>
            {hidden.length > 0 ? (
                <button
                    type="button"
                    onClick={() => setShowUnread((current) => !current)}
                    className="text-xs text-zinc-500 underline hover:text-zinc-800"
                >
                    {showUnread
                        ? 'Ocultar campos não lidos'
                        : `Mostrar ${hidden.length} ${hidden.length === 1 ? 'campo não lido' : 'campos não lidos'}`}
                </button>
            ) : null}
        </div>
    )
}
