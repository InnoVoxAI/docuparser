import { useEffect } from 'react'
import { useOutletContext } from 'react-router'
import { X } from 'lucide-react'
import { Alert } from '../../../shared/components'
// Dependência cruzada legítima (mesma exceção documentada em
// `ValidationRoute.tsx` / `contracts/module-boundaries.md`): a Visão Geral de
// Processos reaproveita a tela de Validação inteira em vez de duplicá-la.
import { ValidationView } from '../../documents'
import { useSchemasQuery } from '../../settings'
import type { AppOutletContext } from '../../../types'

/** Drawer full-height à direita com a tela de Validação existente, aberto ao
 * clicar na caixa "Validação" de um processo que aguarda decisão humana. */
export function ValidationDrawer({
    documentId,
    onClose,
    onValidated,
}: {
    documentId: string
    onClose: () => void
    onValidated: () => void | Promise<unknown>
}) {
    const { selectedDocument, selectedDocumentId, selectDocument, refreshData } = useOutletContext<AppOutletContext>()
    const { data: schemas } = useSchemasQuery()

    // `AppLayout` carrega o Document completo (necessário pra ValidationView)
    // quando `selectedDocumentId` muda — pedimos a seleção ao montar.
    useEffect(() => {
        selectDocument(documentId)
        return () => selectDocument('')
    }, [documentId, selectDocument])

    const ready = selectedDocumentId === documentId && selectedDocument?.id === documentId

    const handleValidated = async () => {
        await refreshData(true)
        await onValidated()
    }

    return (
        <div
            className="fixed inset-0 z-40 flex justify-end bg-black/40"
            onClick={(event) => {
                if (event.target === event.currentTarget) onClose()
            }}
            onKeyDown={(event) => {
                if (event.key === 'Escape') onClose()
            }}
            role="button"
            tabIndex={0}
            aria-label="Fechar validação"
        >
            <aside
                className="flex h-full w-full max-w-2xl flex-col overflow-y-auto bg-zinc-50 shadow-xl"
                role="dialog"
                aria-modal="true"
                aria-label="Validação do processo"
            >
                <header className="sticky top-0 z-10 flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-3">
                    <h2 className="truncate text-sm font-semibold text-zinc-800">
                        Validação — {selectedDocument?.original_filename ?? 'carregando...'}
                    </h2>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Fechar"
                        className="shrink-0 text-zinc-400 hover:text-zinc-700"
                    >
                        <X size={20} aria-hidden="true" />
                    </button>
                </header>
                <div className="p-4">
                    {ready ? (
                        <ValidationView
                            schemas={schemas}
                            selectedDocument={selectedDocument}
                            selectedDocumentId={documentId}
                            onValidated={handleValidated}
                            onBackToInbox={onClose}
                        />
                    ) : (
                        <Alert>Carregando dados do processo...</Alert>
                    )}
                </div>
            </aside>
        </div>
    )
}
