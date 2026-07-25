import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router'
import { Alert } from '../shared/components'
import { readError, navPath } from '../shared/utils'
import { api } from '../shared/lib/http'
import { useAuth } from '../modules/auth'
import { RejectedDocumentModal, useDocumentMutations } from '../modules/documents'
import type { AppOutletContext, Document } from '../types'
import { activeViewForPath } from './navigation'
import { AppSidebar } from './AppSidebar'
import { MobileNav } from './MobileNav'
import { AppHeader } from './AppHeader'

export function AppLayout() {
    const { user, logout, hasPermission, currentTenant } = useAuth()
    const { reprocessDocument, deleteDocument } = useDocumentMutations()
    const location = useLocation()
    const navigate = useNavigate()
    const activeView = activeViewForPath(location.pathname)
    const [selectedDocumentId, setSelectedDocumentId] = useState('')
    const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [rejectedModal, setRejectedModal] = useState<Document | null>(null)
    // Sinal incrementado para forçar as listagens paginadas a recarregar a página
    // atual após ações externas (upload, reprocessar, excluir, "Atualizar").
    const [refreshSignal, setRefreshSignal] = useState(0)

    // feature 009: as listagens (Dashboard/Inbox/Aprovados/Rejeitados) passaram a
    // buscar suas próprias páginas server-side. Aqui só carregamos o documento
    // selecionado (Validação); schemas/layouts saíram completamente (T036-T040,
    // ver comentário de `AppOutletContext` acima); os documentos não são mais
    // carregados em massa no cliente.
    const refreshData = async (silent = false) => {
        setRefreshSignal((n) => n + 1)
        if (!hasPermission('inbox.view')) return
        if (!silent) setLoading(true)
        setError('')
        try {
            if (selectedDocumentId) {
                const detailResponse = await api.get<Document>(`/documents/${selectedDocumentId}`)
                setSelectedDocument(detailResponse.data)
            }
        } catch (requestError) {
            setError(readError(requestError, 'Nao foi possivel carregar os dados operacionais.'))
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        refreshData()
    }, [])

    useEffect(() => {
        if (!selectedDocumentId) {
            setSelectedDocument(null)
            return
        }

        let ignore = false
        api.get<Document>(`/documents/${selectedDocumentId}`)
            .then((response) => {
                if (!ignore) {
                    setSelectedDocument(response.data)
                }
            })
            .catch((requestError) => {
                if (!ignore) {
                    setError(readError(requestError, 'Nao foi possivel carregar o documento.'))
                }
            })

        return () => {
            ignore = true
        }
    }, [selectedDocumentId])

    const navigateToValidation = (documentId: string) => {
        setSelectedDocumentId(documentId)
        navigate(navPath('validation'))
    }

    const handleReprocessDocument = async (id: string) => {
        try {
            await reprocessDocument(id)
            await refreshData()
        } catch (requestError) {
            setError(readError(requestError, 'Falha ao reprocessar documento.'))
        }
    }

    const handleDeleteDocument = async (id: string) => {
        if (!window.confirm('Excluir este documento permanentemente?')) return
        try {
            await deleteDocument(id)
            await refreshData()
        } catch (requestError) {
            setError(readError(requestError, 'Falha ao excluir documento.'))
        }
    }

    return (
        <div className="min-h-screen bg-zinc-50 text-zinc-950">
            <div className="flex min-h-screen">
                <AppSidebar
                    userName={user?.name}
                    currentTenant={currentTenant}
                    activeView={activeView}
                    onLogout={logout}
                />

                <main className="min-w-0 flex-1">
                    <AppHeader activeView={activeView} onRefresh={refreshData} />
                    <MobileNav activeView={activeView} />

                    <section className="px-4 py-5 md:px-6">
                        {error ? <Alert tone="error">{error}</Alert> : null}
                        {loading ? <Alert>Carregando dados...</Alert> : null}

                        <Outlet
                            context={
                                {
                                    selectedDocumentId,
                                    selectedDocument,
                                    refreshSignal,
                                    refreshData,
                                    navigateToValidation,
                                    handleReprocessDocument,
                                    handleDeleteDocument,
                                    onSelectRejected: setRejectedModal,
                                } satisfies AppOutletContext
                            }
                        />
                    </section>
                </main>
            </div>
            {rejectedModal ? (
                <RejectedDocumentModal
                    doc={rejectedModal}
                    onClose={() => setRejectedModal(null)}
                    onReprocess={handleReprocessDocument}
                    onDelete={handleDeleteDocument}
                />
            ) : null}
        </div>
    )
}
