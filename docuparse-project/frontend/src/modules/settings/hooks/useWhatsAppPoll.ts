import { useState } from 'react'
import { comApi } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import { useAuth } from '../../auth'

/**
 * `pollWhatsApp` (POST `/whatsapp/poll`) — a única ação real da aba WhatsApp
 * (ver decisão #2 do handoff de T036-T040: sem schema/useForm, não há nada
 * para validar). Vivia em `SettingsView` usando o `message` compartilhado de
 * toda a tela; agora é um hook próprio com mensagem local, no mesmo espírito
 * de auto-contenção da decisão #3 (aplicada aqui à única ação desta aba, já
 * que `WhatsAppSettingsPanel` continua puramente apresentacional/recebendo
 * `onPoll` por prop, exatamente como no original).
 */
export function useWhatsAppPoll() {
    const { currentTenant } = useAuth()
    const [message, setMessage] = useState('')

    const pollWhatsApp = async () => {
        setMessage('')
        try {
            const response = await comApi.post('/whatsapp/poll', null, { params: { tenant_id: currentTenant ?? '' } })
            const imported = response.data.accepted_count || 0
            const duplicates = response.data.duplicate_count || 0
            let pollMsg = `Captura WhatsApp executada: ${imported} documento(s) importado(s).`
            if (duplicates > 0) {
                pollMsg += ` ${duplicates} já existia(m) no sistema e foi(ram) ignorado(s).`
            }
            setMessage(pollMsg)
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao executar captura WhatsApp.'))
        }
    }

    return { message, pollWhatsApp }
}
