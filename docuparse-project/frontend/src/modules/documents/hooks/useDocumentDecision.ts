import { useState } from 'react'
import { readError } from '../../../shared/utils'
import { useDocumentMutations } from './useDocumentMutations'
import type { Document, FieldRow } from '../types'

/**
 * Notas de rejeição + submissão da decisão (aprovar/rejeitar) — extraído de
 * `ValidationView` só por limite de linhas (FR-012/SC-002).
 */
export function useDocumentDecision({
    selectedDocument,
    selectedDocumentId,
    fieldRows,
    onValidated,
    onBackToInbox,
}: {
    selectedDocument: Document | null
    selectedDocumentId: string
    fieldRows: FieldRow[]
    onValidated: () => void | Promise<unknown>
    onBackToInbox: () => void
}) {
    const { validateDocument } = useDocumentMutations()
    const [notes, setNotes] = useState('')
    const [notesError, setNotesError] = useState(false)
    const [submitError, setSubmitError] = useState('')
    const [submitting, setSubmitting] = useState(false)

    const submitDecision = async (decision: 'approved' | 'rejected') => {
        if (!selectedDocumentId) return
        setSubmitError('')
        setNotesError(false)

        if (!selectedDocument?.extraction_result) {
            setSubmitError('Execute a extração de campos antes de aprovar ou rejeitar.')
            return
        }
        if (decision === 'rejected' && !notes.trim()) {
            setNotesError(true)
            setSubmitError('O motivo da rejeição é obrigatório.')
            return
        }

        setSubmitting(true)
        try {
            await validateDocument({
                id: selectedDocumentId,
                decision,
                notes,
                correctedFields: Object.fromEntries(
                    fieldRows.filter((row) => row.name.trim()).map((row) => [row.name.trim(), row.value]),
                ),
            })
            setNotes('')
            setSubmitError('')
            await onValidated()
            onBackToInbox()
        } catch (requestError) {
            setSubmitError(readError(requestError, 'Falha ao registrar decisão.'))
        } finally {
            setSubmitting(false)
        }
    }

    return { notes, setNotes, notesError, setNotesError, submitError, submitting, submitDecision }
}
