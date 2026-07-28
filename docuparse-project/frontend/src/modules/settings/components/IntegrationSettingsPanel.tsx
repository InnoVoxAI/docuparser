import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { CheckCircle2 } from 'lucide-react'
import { Alert, Field } from '../../../shared/components'
import { api } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import { useAuth } from '../../auth'
import { INTEGRATION_SETTINGS_DEFAULTS, integrationSettingsSchema } from '../schemas/integrationSettingsSchema'
import { ConfigIntro } from './ConfigIntro'

export function IntegrationSettingsPanel() {
    const { currentTenant } = useAuth()
    const [message, setMessage] = useState('')
    const { register, control, handleSubmit, reset } = useForm({
        resolver: zodResolver(integrationSettingsSchema),
        defaultValues: INTEGRATION_SETTINGS_DEFAULTS,
    })

    useEffect(() => {
        let ignore = false
        api.get('/settings/integrations', { params: { tenant: currentTenant ?? '' } })
            .then((response) => {
                if (!ignore) reset({ ...INTEGRATION_SETTINGS_DEFAULTS, ...response.data })
            })
            .catch((requestError) => {
                if (!ignore)
                    setMessage(readError(requestError, 'Nao foi possivel carregar configuracoes de integracao.'))
            })
        return () => {
            ignore = true
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const onSave = handleSubmit(async (values) => {
        setMessage('')
        try {
            const response = await api.patch('/settings/integrations', values)
            reset({ ...INTEGRATION_SETTINGS_DEFAULTS, ...values, ...response.data })
            setMessage('Configuracoes de integracao salvas.')
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao salvar configuracoes de integracao.'))
        }
    })

    return (
        <div className="space-y-4 p-4">
            {message ? <Alert>{message}</Alert> : null}
            <ConfigIntro
                title="Integracoes"
                text="Configure o destino dos dados aprovados. Por enquanto o caminho intermediario e exportacao JSON; Superlogica fica preparado para quando houver acesso ao ambiente."
            />
            <div className="flex justify-end">
                <button
                    type="button"
                    onClick={onSave}
                    className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700"
                >
                    <CheckCircle2 size={16} aria-hidden="true" />
                    Salvar integracoes
                </button>
            </div>
            <div className="grid gap-4 xl:grid-cols-2">
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Export JSON</div>
                    <div className="grid gap-3">
                        <Field label="Ativar exportacao aprovada">
                            <Controller
                                name="approved_export_enabled"
                                control={control}
                                render={({ field }) => (
                                    <select
                                        className="input"
                                        value={field.value ? 'enabled' : 'disabled'}
                                        onChange={(event) => field.onChange(event.target.value === 'enabled')}
                                    >
                                        <option value="enabled">Ativado</option>
                                        <option value="disabled">Desativado</option>
                                    </select>
                                )}
                            />
                        </Field>
                        <Field label="Diretorio destino">
                            <input className="input" {...register('approved_export_dir')} />
                        </Field>
                        <Field label="Formato">
                            <select className="input" {...register('approved_export_format')}>
                                <option value="json">JSON</option>
                                <option value="jsonl">JSONL</option>
                            </select>
                        </Field>
                    </div>
                </section>
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Superlogica futuro</div>
                    <div className="grid gap-3">
                        <Field label="Base URL sandbox">
                            <input className="input" {...register('superlogica_base_url')} placeholder="https://..." />
                        </Field>
                        <Field label="Credencial">
                            <input
                                className="input"
                                type="password"
                                placeholder="Nao persistido por enquanto"
                                disabled
                            />
                        </Field>
                        <Field label="Modo de envio">
                            <select className="input" {...register('superlogica_mode')}>
                                <option value="disabled">Desativado ate liberar acesso</option>
                                <option value="mock">Mock</option>
                                <option value="sandbox">Sandbox</option>
                            </select>
                        </Field>
                    </div>
                </section>
            </div>
        </div>
    )
}
