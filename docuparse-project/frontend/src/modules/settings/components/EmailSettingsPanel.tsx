import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { CheckCircle2, RefreshCw } from 'lucide-react'
import { Alert } from '../../../shared/components'
import { api, comApi } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import { useAuth } from '../../auth'
import {
    EMAIL_SETTINGS_DEFAULTS,
    emailSettingsSchema,
    type EmailSettingsFormValues,
} from '../schemas/emailSettingsSchema'
import { ConfigIntro } from './ConfigIntro'
import { EmailAccountFields } from './EmailAccountFields'
import { EmailAttachmentRules } from './EmailAttachmentRules'

/**
 * "Testar captura IMAP" preserva o pré-check imperativo original (host/
 * usuário obrigatórios só quando `provider === 'imap'`, só para o botão de
 * teste — nunca para "Salvar email"): decisão #4 do handoff de T036-T040.
 * Não é um `.refine` do schema Zod porque isso bloquearia também o save, que
 * hoje aceita host/usuário vazios.
 */
export function EmailSettingsPanel() {
    const { currentTenant } = useAuth()
    const [message, setMessage] = useState('')
    const {
        register,
        control,
        handleSubmit,
        getValues,
        reset,
        formState: { errors },
    } = useForm({
        resolver: zodResolver(emailSettingsSchema),
        defaultValues: EMAIL_SETTINGS_DEFAULTS,
    })

    useEffect(() => {
        let ignore = false
        api.get('/settings/email', { params: { tenant: currentTenant ?? '' } })
            .then((response) => {
                if (!ignore) reset({ ...EMAIL_SETTINGS_DEFAULTS, ...response.data })
            })
            .catch((requestError) => {
                if (!ignore) setMessage(readError(requestError, 'Nao foi possivel carregar configuracoes de email.'))
            })
        return () => {
            ignore = true
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const submitEmail = async (values: EmailSettingsFormValues): Promise<boolean> => {
        setMessage('')
        try {
            const response = await api.patch('/settings/email', values)
            reset({ ...EMAIL_SETTINGS_DEFAULTS, ...values, ...response.data })
            setMessage('Configuracoes de email salvas.')
            return true
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao salvar configuracoes de email.'))
            return false
        }
    }

    const onSave = handleSubmit((values) => submitEmail(values))

    const onPoll = async () => {
        setMessage('')
        const values = getValues()
        if (values.provider === 'imap') {
            if (!values.imap_host?.trim()) {
                setMessage('Preencha o campo "Host IMAP" antes de testar (ex: imap.gmail.com).')
                return
            }
            if (!values.username?.trim()) {
                setMessage('Preencha o campo "Usuario" com o endereco de email monitorado.')
                return
            }
        }
        let saved = false
        await handleSubmit(async (validValues) => {
            saved = await submitEmail(validValues)
        })()
        if (!saved) return
        try {
            const response = await comApi.post('/email/poll', null, { params: { tenant_id: currentTenant ?? '' } })
            const imported = response.data.accepted_count || 0
            const duplicates = response.data.duplicate_count || 0
            let pollMsg = `Captura IMAP executada: ${imported} documento(s) importado(s).`
            if (duplicates > 0) {
                pollMsg += ` ${duplicates} já existia(m) no sistema e foi(ram) ignorado(s).`
            }
            setMessage(pollMsg)
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao executar captura IMAP.'))
        }
    }

    return (
        <div className="space-y-4 p-4">
            {message ? <Alert>{message}</Alert> : null}
            <ConfigIntro
                title="Email"
                text="Configure como documentos chegam por email. A senha/app password continua fora do banco e deve estar em DOCUPARSE_IMAP_PASSWORD no servidor."
            />
            <div className="flex flex-wrap justify-end gap-2">
                <button
                    type="button"
                    onClick={onPoll}
                    className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                >
                    <RefreshCw size={16} aria-hidden="true" />
                    Testar captura IMAP
                </button>
                <button
                    type="button"
                    onClick={onSave}
                    className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700"
                >
                    <CheckCircle2 size={16} aria-hidden="true" />
                    Salvar email
                </button>
            </div>
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
                <EmailAccountFields register={register} control={control} errors={errors} />
                <EmailAttachmentRules register={register} errors={errors} />
            </div>
        </div>
    )
}
