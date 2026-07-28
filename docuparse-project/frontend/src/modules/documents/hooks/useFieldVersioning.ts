import { useState } from 'react'
import { api } from '../../../shared/lib/http'
import { asApiError, readError } from '../../../shared/utils'
import { parseFieldEntry } from '../utils'
import type { Document, ExtractionFieldVersion, FieldRow, FieldVersionsResponse, SaveMessage } from '../types'

/**
 * Salvar campos (versionamento, feature 007) e histórico (somente leitura) —
 * extraído de `ValidationView` só por limite de linhas (FR-012/SC-002).
 */
export function useFieldVersioning({
    selectedDocument,
    selectedDocumentId,
    fieldRows,
    setFieldRows,
    onValidated,
}: {
    selectedDocument: Document | null
    selectedDocumentId: string
    fieldRows: FieldRow[]
    setFieldRows: (rows: FieldRow[]) => void
    onValidated: () => void | Promise<unknown>
}) {
    const [saving, setSaving] = useState(false)
    const [saveMessage, setSaveMessage] = useState<SaveMessage | null>(null)
    const [confirmSaveOpen, setConfirmSaveOpen] = useState(false)
    const [historyOpen, setHistoryOpen] = useState(false)
    const [history, setHistory] = useState<FieldVersionsResponse | null>(null)
    const [historyLoading, setHistoryLoading] = useState(false)
    const [historyError, setHistoryError] = useState('')

    const buildFieldsPayload = () =>
        fieldRows.filter((row) => row.name.trim()).map((row) => ({ name: row.name.trim(), value: row.value }))

    const handleSaveFields = async () => {
        setConfirmSaveOpen(false)
        if (!selectedDocumentId) return
        setSaving(true)
        setSaveMessage(null)
        try {
            const response = await api.put<ExtractionFieldVersion>(`/documents/${selectedDocumentId}/fields`, {
                base_version_number: selectedDocument?.active_field_version_number ?? null,
                fields: buildFieldsPayload(),
            })
            // Reflete a versão salva (campos editados/adicionados com confiança 100%).
            setFieldRows(
                Object.entries(response.data.fields || {}).map(([name, raw]) => {
                    const { value, confidence } = parseFieldEntry(raw)
                    return { name, value, confidence }
                }),
            )
            setSaveMessage({ tone: 'success', text: `Versão ${response.data.version_number} salva com sucesso.` })
            await onValidated()
        } catch (requestError) {
            const statusCode = asApiError(requestError).response?.status
            if (statusCode === 409) {
                const active = asApiError(requestError).response?.data?.active_version_number
                setSaveMessage({
                    tone: 'error',
                    text: `A lista foi atualizada por outro processo (versão ativa atual: ${active}). Recarregue a versão ativa antes de salvar.`,
                })
                await onValidated()
            } else {
                setSaveMessage({ tone: 'error', text: readError(requestError, 'Falha ao salvar alterações.') })
            }
        } finally {
            setSaving(false)
        }
    }

    const openHistory = async () => {
        setHistoryOpen(true)
        setHistoryLoading(true)
        setHistoryError('')
        setHistory(null)
        try {
            const response = await api.get<FieldVersionsResponse>(`/documents/${selectedDocumentId}/field-versions`)
            setHistory(response.data)
        } catch (requestError) {
            setHistoryError(readError(requestError, 'Falha ao carregar o histórico de versões.'))
        } finally {
            setHistoryLoading(false)
        }
    }

    return {
        saving,
        saveMessage,
        confirmSaveOpen,
        setConfirmSaveOpen,
        handleSaveFields,
        historyOpen,
        setHistoryOpen,
        history,
        historyLoading,
        historyError,
        openHistory,
    }
}
