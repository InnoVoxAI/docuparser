import type { FieldErrors, UseFormRegister } from 'react-hook-form'
import { Field } from '../../../shared/components'
import type { EmailSettingsFormValues } from '../schemas/emailSettingsSchema'

export function EmailAttachmentRules({
    register,
    errors,
}: {
    register: UseFormRegister<EmailSettingsFormValues>
    errors: FieldErrors<EmailSettingsFormValues>
}) {
    return (
        <section className="rounded-md border border-zinc-200 p-4">
            <div className="mb-3 text-sm font-semibold">Regras de anexos</div>
            <div className="space-y-3">
                <Field label="Tipos aceitos">
                    <input className="input" {...register('accepted_content_types')} />
                </Field>
                <Field label="Tamanho maximo MB">
                    <input
                        className="input"
                        type="number"
                        min="1"
                        max="200"
                        {...register('max_attachment_mb', { valueAsNumber: true })}
                    />
                    {errors.max_attachment_mb ? (
                        <p className="mt-1 text-xs text-red-600">Informe um valor entre 1 e 200.</p>
                    ) : null}
                </Field>
                <Field label="Remetentes bloqueados">
                    <textarea
                        className="input min-h-[90px]"
                        {...register('blocked_senders')}
                        placeholder="um email por linha"
                    />
                </Field>
            </div>
        </section>
    )
}
