import { Controller, type Control, type FieldErrors, type UseFormRegister } from 'react-hook-form'
import { Field } from '../../../shared/components'
import type { EmailSettingsFormValues } from '../schemas/emailSettingsSchema'

export function EmailAccountFields({
    register,
    control,
    errors,
}: {
    register: UseFormRegister<EmailSettingsFormValues>
    control: Control<EmailSettingsFormValues>
    errors: FieldErrors<EmailSettingsFormValues>
}) {
    return (
        <section className="rounded-md border border-zinc-200 p-4">
            <div className="mb-3 text-sm font-semibold">Conta de captura</div>
            <div className="grid gap-3 md:grid-cols-2">
                <Field label="Provider">
                    <select className="input" {...register('provider')}>
                        <option value="imap">IMAP</option>
                        <option value="webhook">Webhook</option>
                        <option value="manual_test">Teste manual</option>
                    </select>
                </Field>
                <Field label="Ativo">
                    <Controller
                        name="is_active"
                        control={control}
                        render={({ field }) => (
                            <select
                                className="input"
                                value={field.value ? 'enabled' : 'disabled'}
                                onChange={(event) => field.onChange(event.target.value === 'enabled')}
                            >
                                <option value="enabled">Ativo</option>
                                <option value="disabled">Inativo</option>
                            </select>
                        )}
                    />
                </Field>
                <Field label="Pasta monitorada">
                    <input className="input" {...register('inbox_folder')} />
                </Field>
                <Field label="Host IMAP">
                    <input className="input" {...register('imap_host')} placeholder="imap.exemplo.com" />
                </Field>
                <Field label="Porta">
                    <input
                        className="input"
                        type="number"
                        min="1"
                        max="65535"
                        {...register('imap_port', { valueAsNumber: true })}
                    />
                    {errors.imap_port ? <p className="mt-1 text-xs text-red-600">Porta invalida.</p> : null}
                </Field>
                <Field label="Usuario">
                    <input className="input" {...register('username')} placeholder="documentos@empresa.com" />
                </Field>
                <Field label="Senha/app password">
                    <input className="input" type="password" placeholder="Nao persistido por enquanto" disabled />
                </Field>
                <Field label="Webhook URL">
                    <input className="input" {...register('webhook_url')} />
                </Field>
            </div>
        </section>
    )
}
