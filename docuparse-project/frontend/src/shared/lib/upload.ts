import { comApi } from './http'

/** Envio manual de documento (mesmo endpoint usado pela tela de Upload e pelo
 * atalho "Novo processo" da Visão Geral). */
export async function uploadManualDocument(file: File, sender?: string) {
    const formData = new FormData()
    formData.append('file', file)
    if (sender?.trim()) {
        formData.append('sender', sender)
    }
    const response = await comApi.post<{ document_id: string }>('/documents/manual', formData)
    return response.data
}
