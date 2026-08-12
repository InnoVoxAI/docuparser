import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { CheckCircle2 } from 'lucide-react'
import { Alert } from '../../../shared/components'
import { api } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import { useAuth } from '../../auth'
import { OCR_SETTINGS_DEFAULTS, ocrSettingsSchema } from '../schemas/ocrSettingsSchema'
import { ConfigIntro } from './ConfigIntro'
import { OcrRoutingSummary } from './OcrRoutingSummary'
import { OcrSettingsFields } from './OcrSettingsFields'

/**
 * Primeiro uso de RHF+Zod no codebase (T036/T037). GET-on-mount + PATCH ficam
 * self-contained aqui (settings/ocr NÃO entra em TanStack Query — decisão #3
 * do handoff de T036-T040); a mensagem de sucesso/erro, antes um `message`
 * compartilhado por toda `SettingsView`, agora é local a este painel (mesma
 * categoria de relocação de UI já documentada por T034 para `bannerMessage`).
 */
export function OcrSettingsPanel() {
    const { currentTenant } = useAuth()
    const [message, setMessage] = useState('')
    const {
        register,
        control,
        handleSubmit,
        reset,
        watch,
        formState: { errors },
    } = useForm({
        resolver: zodResolver(ocrSettingsSchema),
        defaultValues: OCR_SETTINGS_DEFAULTS,
    })

    useEffect(() => {
        let ignore = false
        api.get('/settings/ocr', { params: { tenant: currentTenant ?? '' } })
            .then((response) => {
                // Preserva o comportamento original de "merge sobre defaults": um
                // GET parcial/vazio (comum nos handlers MSW de teste) não deve apagar
                // os valores numéricos padrão.
                if (!ignore) reset({ ...OCR_SETTINGS_DEFAULTS, ...response.data })
            })
            .catch((requestError) => {
                if (!ignore) setMessage(readError(requestError, 'Nao foi possivel carregar configuracoes de OCR.'))
            })
        return () => {
            ignore = true
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const onSave = handleSubmit(async (values) => {
        setMessage('')
        try {
            const response = await api.patch('/settings/ocr', values)
            reset({ ...OCR_SETTINGS_DEFAULTS, ...values, ...response.data })
            setMessage('Configuracoes de OCR salvas.')
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao salvar configuracoes de OCR.'))
        }
    })

    return (
        <div className="space-y-4 p-4">
            {message ? <Alert>{message}</Alert> : null}
            <ConfigIntro
                title="OCR"
                text="Perfil operacional atual do OCR. A tela mostra somente os engines usados de fato no fluxo automatico: Docling para PDF textual, OpenRouter para imagem/PDF escaneado e Tesseract como fallback tecnico."
            />
            <div className="flex justify-end">
                <button
                    type="button"
                    onClick={onSave}
                    className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700"
                >
                    <CheckCircle2 size={16} aria-hidden="true" />
                    Salvar OCR
                </button>
            </div>
            <div className="grid gap-4 xl:grid-cols-2">
                <OcrRoutingSummary settings={watch()} />
                <OcrSettingsFields register={register} control={control} errors={errors} />
            </div>
        </div>
    )
}
