import React, { useEffect, useMemo, useRef, useState } from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import {
    AlertTriangle,
    CheckCircle2,
    ClipboardCheck,
    Eye,
    FileText,
    Inbox,
    LayoutDashboard,
    RefreshCw,
    Settings,
    Trash2,
    Upload,
    X,
    XCircle,
} from 'lucide-react'
import './index.css'
import { BOLETO_DEFAULT_SCHEMA_ID, BOLETO_DEFAULT_MODEL_NAME, BOLETO_DEFAULT_FIELDS, isLikelyBoletoText } from './models/boleto/schemas'
import { boletoPromptForDocumentType } from './models/boleto/prompts'
import { BOLETO_DEFAULT_EXAMPLES } from './models/boleto/examples'
import { BOLETO_DEFAULT_RULES } from './models/boleto/rules'
import { NOTA_FISCAL_DEFAULT_SCHEMA_ID, NOTA_FISCAL_DEFAULT_MODEL_NAME, NOTA_FISCAL_DEFAULT_FIELDS, isLikelyNotaFiscalText } from './models/nota_fiscal/schemas'
import { notaFiscalPromptForDocumentType } from './models/nota_fiscal/prompts'
import { NOTA_FISCAL_DEFAULT_EXAMPLES } from './models/nota_fiscal/examples'
import { NOTA_FISCAL_DEFAULT_RULES } from './models/nota_fiscal/rules'
import { CONTA_AGUA_DEFAULT_SCHEMA_ID, CONTA_AGUA_DEFAULT_MODEL_NAME, CONTA_AGUA_DEFAULT_FIELDS, isLikelyContaAguaText } from './models/contadeagua/schemas'
import { contaAguaPromptForDocumentType } from './models/contadeagua/prompts'
import { CONTA_AGUA_DEFAULT_EXAMPLES } from './models/contadeagua/examples'
import { CONTA_AGUA_DEFAULT_RULES } from './models/contadeagua/rules'
import { DEFAULT_SCHEMA_ID, DEFAULT_MODEL_NAME, DEFAULT_LANGEXTRACT_FIELDS } from './models/recibo/schemas'
import { DEFAULT_LANGEXTRACT_PROMPT } from './models/recibo/prompts'

const internalServiceToken = import.meta.env.VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN
const authHeaders = internalServiceToken ? { Authorization: `Bearer ${internalServiceToken}` } : {}
const api = axios.create({ baseURL: '/api/ocr', headers: authHeaders })
const comApi = axios.create({ baseURL: '/com/api/v1', headers: authHeaders })

const NAV_ITEMS = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'inbox', label: 'Inbox', icon: Inbox },
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'validation', label: 'Validacao', icon: ClipboardCheck },
    { id: 'operations', label: 'Operacoes', icon: AlertTriangle },
    { id: 'settings', label: 'Configuracoes', icon: Settings },
]

const STATUS_LABELS = {
    RECEIVED: 'Recebido',
    OCR_COMPLETED: 'OCR concluido',
    OCR_FAILED: 'OCR falhou',
    LAYOUT_CLASSIFIED: 'Layout classificado',
    EXTRACTION_COMPLETED: 'Extracao concluida',
    VALIDATION_PENDING: 'Validacao pendente',
    APPROVED: 'Aprovado',
    REJECTED: 'Rejeitado',
    ERP_INTEGRATION_REQUESTED: 'ERP solicitado',
    ERP_SENT: 'ERP enviado',
    ERP_FAILED: 'ERP falhou',
}

const TYPE_ALIASES = {
    pdf: ['digital_pdf'],
    scan: ['scanned_image'],
    escaneado: ['scanned_image'],
    imagem: ['scanned_image'],
    manuscrito: ['handwritten', 'manuscrito'],
}

function filterDocuments(docs, query) {
    if (!query.trim()) return docs
    const q = query.trim().toLowerCase()
    return docs.filter((doc) => {
        const filename = (doc.original_filename || doc.id || '').toLowerCase()
        const status = (doc.status || '').toLowerCase()
        const statusLabel = (STATUS_LABELS[doc.status] || '').toLowerCase()
        const docType = (doc.document_type || '').toLowerCase()
        const channel = (doc.channel || '').toLowerCase()
        if (filename.includes(q) || status.includes(q) || statusLabel.includes(q) || docType.includes(q) || channel.includes(q)) return true
        const aliasTypes = TYPE_ALIASES[q]
        return aliasTypes ? aliasTypes.some((t) => docType.includes(t)) : false
    })
}

function App() {
    const [activeView, setActiveView] = useState('dashboard')
    const [documents, setDocuments] = useState([])
    const [schemas, setSchemas] = useState([])
    const [layouts, setLayouts] = useState([])
    const [selectedDocumentId, setSelectedDocumentId] = useState('')
    const [selectedDocument, setSelectedDocument] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const refreshData = async () => {
        setLoading(true)
        setError('')
        try {
            const [documentsResult, schemasResult, layoutsResult] = await Promise.allSettled([
                api.get('/documents'),
                api.get('/schema-configs'),
                api.get('/layout-configs'),
            ])

            if (documentsResult.status === 'fulfilled') {
                setDocuments(documentsResult.value.data ?? [])
            } else {
                setError(readError(documentsResult.reason, 'Nao foi possivel carregar os documentos.'))
            }

            if (schemasResult.status === 'fulfilled') {
                setSchemas(schemasResult.value.data ?? [])
            }

            if (layoutsResult.status === 'fulfilled') {
                setLayouts(layoutsResult.value.data ?? [])
            }

            const configError = [schemasResult, layoutsResult].find((result) => result.status === 'rejected')
            if (documentsResult.status === 'fulfilled' && configError) {
                setError(readError(configError.reason, 'Documentos carregados, mas nao foi possivel carregar todas as configuracoes.'))
            }

            if (selectedDocumentId) {
                const detailResponse = await api.get(`/documents/${selectedDocumentId}`)
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
        api.get(`/documents/${selectedDocumentId}`)
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

    const metrics = useMemo(() => buildMetrics(documents), [documents])
    const pendingDocuments = useMemo(
        () => documents.filter((document) => ['RECEIVED', 'OCR_COMPLETED', 'EXTRACTION_COMPLETED', 'VALIDATION_PENDING'].includes(document.status)),
        [documents],
    )

    const handleDocumentUpdated = (updatedDocument) => {
        setSelectedDocument(updatedDocument)
        setDocuments((currentDocuments) => currentDocuments.map((document) => (
            document.id === updatedDocument.id
                ? {
                    ...document,
                    status: updatedDocument.status,
                    document_type: updatedDocument.document_type,
                    layout: updatedDocument.layout,
                    updated_at: updatedDocument.updated_at,
                }
                : document
        )))
    }

    return (
        <div className="min-h-screen bg-zinc-50 text-zinc-950">
            <div className="flex min-h-screen">
                <aside className="hidden w-64 shrink-0 border-r border-zinc-200 bg-white md:block">
                    <div className="border-b border-zinc-200 px-5 py-5">
                        <div className="text-lg font-semibold">DocuParse</div>
                        <div className="mt-1 text-xs text-zinc-500">Operacao de documentos</div>
                    </div>
                    <nav className="space-y-1 px-3 py-4">
                        {NAV_ITEMS.map((item) => (
                            <NavButton
                                key={item.id}
                                item={item}
                                active={activeView === item.id}
                                onClick={() => setActiveView(item.id)}
                            />
                        ))}
                    </nav>
                </aside>

                <main className="min-w-0 flex-1">
                    <header className="border-b border-zinc-200 bg-white px-4 py-4 md:px-6">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <h1 className="text-xl font-semibold">{viewTitle(activeView)}</h1>
                                <p className="mt-1 text-sm text-zinc-500">Fluxo de captura, validacao e exportacao aprovado.</p>
                            </div>
                            <button
                                type="button"
                                onClick={refreshData}
                                className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                            >
                                <RefreshCw size={16} aria-hidden="true" />
                                Atualizar
                            </button>
                        </div>
                    </header>

                    <div className="border-b border-zinc-200 bg-white px-2 py-2 md:hidden">
                        <div className="flex gap-1 overflow-x-auto">
                            {NAV_ITEMS.map((item) => (
                                <NavButton
                                    key={item.id}
                                    item={item}
                                    active={activeView === item.id}
                                    onClick={() => setActiveView(item.id)}
                                    compact
                                />
                            ))}
                        </div>
                    </div>

                    <section className="px-4 py-5 md:px-6">
                        {error ? <Alert tone="error">{error}</Alert> : null}
                        {loading ? <Alert>Carregando dados...</Alert> : null}

                        {activeView === 'dashboard' ? <Dashboard metrics={metrics} documents={documents} /> : null}
                        {activeView === 'inbox' ? (
                            <InboxView
                                documents={documents}
                                selectedDocumentId={selectedDocumentId}
                                onSelectDocument={setSelectedDocumentId}
                            />
                        ) : null}
                        {activeView === 'upload' ? <UploadView onUploaded={refreshData} /> : null}
                        {activeView === 'validation' ? (
                            <ValidationView
                                documents={pendingDocuments}
                                selectedDocument={selectedDocument}
                                selectedDocumentId={selectedDocumentId}
                                onSelectDocument={setSelectedDocumentId}
                                onDocumentUpdated={handleDocumentUpdated}
                                onDocumentDeleted={() => {
                                    setSelectedDocumentId('')
                                    setSelectedDocument(null)
                                }}
                                onValidated={refreshData}
                            />
                        ) : null}
                        {activeView === 'operations' ? <OperationsView /> : null}
                        {activeView === 'settings' ? <SettingsView schemas={schemas} layouts={layouts} documents={documents} onChanged={refreshData} /> : null}
                    </section>
                </main>
            </div>
        </div>
    )
}

function NavButton({ item, active, onClick, compact = false }) {
    const Icon = item.icon
    return (
        <button
            type="button"
            onClick={onClick}
            className={`flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium ${
                compact ? 'shrink-0' : 'w-full'
            } ${active ? 'bg-zinc-900 text-white' : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950'}`}
        >
            <Icon size={17} aria-hidden="true" />
            {item.label}
        </button>
    )
}

function Dashboard({ metrics, documents }) {
    const [search, setSearch] = useState('')
    const displayed = search.trim() ? filterDocuments(documents, search) : documents.slice(0, 8)
    return (
        <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Metric label="Total" value={metrics.total} />
                <Metric label="Pendentes" value={metrics.pending} />
                <Metric label="Aprovados" value={metrics.approved} />
                <Metric label="Falhas" value={metrics.failed} />
            </div>
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                    <div className="text-sm font-semibold">Ultimos documentos</div>
                    <SearchInput value={search} onChange={setSearch} placeholder="Buscar por nome, status, tipo..." />
                </div>
                <DocumentTable documents={displayed} onSelectDocument={() => {}} />
            </section>
        </div>
    )
}

function InboxView({ documents, selectedDocumentId, onSelectDocument }) {
    const [search, setSearch] = useState('')
    const displayed = filterDocuments(documents, search)
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                <div className="text-sm font-semibold">Documentos recebidos</div>
                <SearchInput value={search} onChange={setSearch} placeholder="Buscar por nome, status, tipo..." />
            </div>
            <DocumentTable documents={displayed} selectedDocumentId={selectedDocumentId} onSelectDocument={onSelectDocument} />
        </section>
    )
}

const DEFAULT_DLQ_STREAM = 'ocr.completed.dlq'

function OperationsView() {
    const [summary, setSummary] = useState({ total: 0, streams: [] })
    const [selectedStream, setSelectedStream] = useState(DEFAULT_DLQ_STREAM)
    const [events, setEvents] = useState([])
    const [selectedEvent, setSelectedEvent] = useState(null)
    const [loading, setLoading] = useState(false)
    const [requeueing, setRequeueing] = useState(false)
    const [message, setMessage] = useState('')
    const [messageTone, setMessageTone] = useState('neutral')

    const loadOperations = async (stream = selectedStream) => {
        setLoading(true)
        setMessage('')
        setMessageTone('neutral')
        try {
            const [summaryResponse, eventsResponse] = await Promise.all([
                api.get('/operations/dlq/summary'),
                api.get('/operations/dlq/events', { params: { stream, limit: 50 } }),
            ])
            setSummary(summaryResponse.data ?? { total: 0, streams: [] })
            setEvents(eventsResponse.data?.entries ?? [])
            setSelectedEvent(null)
        } catch (requestError) {
            setMessage(readError(requestError, 'Nao foi possivel carregar as DLQs.'))
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadOperations(DEFAULT_DLQ_STREAM)
    }, [])

    const selectStream = (stream) => {
        setSelectedStream(stream)
        loadOperations(stream)
    }

    const requeueSelectedEvent = async ({ execute }) => {
        if (!selectedEvent || requeueing) {
            return
        }
        if (execute && !window.confirm('Reenfileirar este payload original para reprocessamento? O registro da DLQ sera mantido para auditoria.')) {
            return
        }
        setRequeueing(true)
        setMessage('')
        setMessageTone('neutral')
        try {
            const response = await api.post('/operations/dlq/requeue', {
                stream: selectedStream,
                id: selectedEvent.id,
                execute,
                requested_by: 'frontend-admin',
            })
            const target = response.data?.target_stream || selectedEvent.original_stream || selectedStream
            if (execute) {
                await loadOperations(selectedStream)
                setMessage(`Evento reenfileirado em ${target}. O item original permanece na DLQ para auditoria.`)
                setMessageTone('neutral')
            } else {
                setMessage(`Simulacao OK: este evento sera enviado para ${target}.`)
                setMessageTone('neutral')
            }
        } catch (requestError) {
            setMessageTone('error')
            setMessage(readError(requestError, 'Nao foi possivel reenfileirar o evento.'))
        } finally {
            setRequeueing(false)
        }
    }

    return (
        <div className="space-y-4">
            {message ? <Alert tone={messageTone}>{message}</Alert> : null}
            {loading ? <Alert>Carregando operacoes...</Alert> : null}
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 px-4 py-3">
                    <div>
                        <div className="text-sm font-semibold">Dead-letter queues</div>
                        <div className="mt-1 text-xs text-zinc-500">Eventos que falharam nos workers e aguardam revisao operacional.</div>
                    </div>
                    <button type="button" onClick={() => loadOperations(selectedStream)} className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100">
                        <RefreshCw size={16} aria-hidden="true" />
                        Atualizar
                    </button>
                </div>
                <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-4">
                    <Metric label="Total em DLQ" value={summary.total || 0} />
                    {(summary.streams || []).map((item) => (
                        <button
                            key={item.stream}
                            type="button"
                            onClick={() => selectStream(item.stream)}
                            className={`rounded-md border p-3 text-left ${selectedStream === item.stream ? 'border-zinc-900 bg-zinc-50' : 'border-zinc-200 bg-white hover:bg-zinc-50'}`}
                        >
                            <div className="truncate text-xs font-semibold uppercase text-zinc-500">{item.stream}</div>
                            <div className="mt-2 text-2xl font-semibold">{item.count}</div>
                            <div className="mt-1 truncate text-xs text-zinc-500">{item.latest?.error_type || 'Sem eventos'}</div>
                        </button>
                    ))}
                </div>
            </section>

            <section className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
                <div className="rounded-md border border-zinc-200 bg-white">
                    <div className="border-b border-zinc-200 px-4 py-3">
                        <div className="text-sm font-semibold">{selectedStream}</div>
                        <div className="mt-1 text-xs text-zinc-500">Selecione um evento para ver erro e payload original.</div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-zinc-200 text-sm">
                            <thead className="bg-zinc-50 text-left text-xs uppercase text-zinc-500">
                                <tr>
                                    <th className="px-4 py-3">Data</th>
                                    <th className="px-4 py-3">Origem</th>
                                    <th className="px-4 py-3">Evento</th>
                                    <th className="px-4 py-3">Erro</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-zinc-100">
                                {events.map((event) => (
                                    <tr
                                        key={event.id}
                                        onClick={() => setSelectedEvent(event)}
                                        className={`cursor-pointer hover:bg-zinc-50 ${selectedEvent?.id === event.id ? 'bg-zinc-50' : ''}`}
                                    >
                                        <td className="whitespace-nowrap px-4 py-3 text-zinc-600">{formatDate(event.occurred_at)}</td>
                                        <td className="whitespace-nowrap px-4 py-3">{event.source || '-'}</td>
                                        <td className="px-4 py-3">
                                            <div className="font-medium">{event.event_type || '-'}</div>
                                            <div className="max-w-[220px] truncate text-xs text-zinc-500">{event.event_id || '-'}</div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="font-medium text-red-700">{event.error_type || '-'}</div>
                                            <div className="max-w-[360px] truncate text-xs text-zinc-500">{event.error || '-'}</div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {events.length === 0 ? <EmptyState icon={AlertTriangle} text="Nenhum evento nesta DLQ." /> : null}
                </div>

                <div className="rounded-md border border-zinc-200 bg-white">
                    <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">Detalhe</div>
                    {selectedEvent ? (
                        <div className="space-y-3 p-4">
                            <KeyValueGrid
                                values={{
                                    stream: selectedEvent.original_stream || selectedStream,
                                    origem: selectedEvent.source || '-',
                                    erro: selectedEvent.error_type || '-',
                                }}
                            />
                            <div className="flex flex-wrap gap-2">
                                <button
                                    type="button"
                                    onClick={() => requeueSelectedEvent({ execute: false })}
                                    disabled={requeueing}
                                    className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    <RefreshCw size={16} aria-hidden="true" />
                                    Simular
                                </button>
                                <button
                                    type="button"
                                    onClick={() => requeueSelectedEvent({ execute: true })}
                                    disabled={requeueing}
                                    className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    <RefreshCw size={16} aria-hidden="true" />
                                    Reenfileirar
                                </button>
                            </div>
                            <div>
                                <div className="mb-1 text-xs font-semibold uppercase text-zinc-500">Mensagem</div>
                                <div className="rounded-md border border-red-100 bg-red-50 p-3 text-sm text-red-800">{selectedEvent.error || '-'}</div>
                            </div>
                            <div>
                                <div className="mb-1 text-xs font-semibold uppercase text-zinc-500">Payload original</div>
                                <pre className="max-h-[420px] overflow-auto rounded-md bg-zinc-950 p-3 text-xs text-zinc-50">{JSON.stringify(selectedEvent.payload || {}, null, 2)}</pre>
                            </div>
                        </div>
                    ) : (
                        <EmptyState icon={FileText} text="Selecione um evento para inspecionar." />
                    )}
                </div>
            </section>
        </div>
    )
}

function UploadView({ onUploaded }) {
    const [file, setFile] = useState(null)
    const [previewUrl, setPreviewUrl] = useState('')
    const [tenantId, setTenantId] = useState('tenant-demo')
    const [sender, setSender] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [message, setMessage] = useState('')

    const canSubmit = Boolean(file) && tenantId.trim() && !submitting

    useEffect(() => {
        if (!file) {
            setPreviewUrl('')
            return
        }
        const url = URL.createObjectURL(file)
        setPreviewUrl(url)
        return () => URL.revokeObjectURL(url)
    }, [file])

    const submitUpload = async () => {
        if (!canSubmit) {
            return
        }
        setSubmitting(true)
        setMessage('')
        const formData = new FormData()
        formData.append('file', file)
        formData.append('tenant_id', tenantId)
        if (sender.trim()) {
            formData.append('sender', sender)
        }

        try {
            const response = await comApi.post('/documents/manual', formData)
            setMessage(`Documento recebido: ${response.data.document_id}`)
            setFile(null)
            await onUploaded()
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha no upload.'))
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,760px)_minmax(320px,1fr)]">
            <section className="rounded-md border border-zinc-200 bg-white p-4">
                <div className="grid gap-4 md:grid-cols-2">
                    <Field label="Tenant">
                        <input value={tenantId} onChange={(event) => setTenantId(event.target.value)} className="input" />
                    </Field>
                    <Field label="Remetente">
                        <input value={sender} onChange={(event) => setSender(event.target.value)} className="input" />
                    </Field>
                    <div className="md:col-span-2">
                        <Field label="Arquivo">
                            <input
                                type="file"
                                accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.webp"
                                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                                className="input file:mr-3 file:rounded-md file:border-0 file:bg-zinc-900 file:px-3 file:py-2 file:text-sm file:text-white"
                            />
                        </Field>
                    </div>
                </div>
                <div className="mt-4 flex items-center gap-3">
                    <button type="button" onClick={submitUpload} disabled={!canSubmit} className="primary-button">
                        <Upload size={16} aria-hidden="true" />
                        {submitting ? 'Enviando' : 'Enviar'}
                    </button>
                    {message ? <span className="text-sm text-zinc-600">{message}</span> : null}
                </div>
            </section>

            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">Preview</div>
                {!previewUrl ? (
                    <EmptyState icon={FileText} text="Selecione PDF ou imagem para visualizar." />
                ) : file?.type === 'application/pdf' ? (
                    <object data={previewUrl} type="application/pdf" className="h-[520px] w-full">
                        <EmptyState icon={FileText} text="Nao foi possivel renderizar o PDF." />
                    </object>
                ) : (
                    <div className="max-h-[520px] overflow-auto p-3">
                        <img src={previewUrl} alt="Preview do arquivo selecionado" className="max-w-full rounded border border-zinc-200" />
                    </div>
                )}
            </section>
        </div>
    )
}

function ValidationView({ documents, selectedDocument, selectedDocumentId, onSelectDocument, onDocumentUpdated, onDocumentDeleted, onValidated }) {
    const [notes, setNotes] = useState('')
    const [validationSearch, setValidationSearch] = useState('')
    const [fieldRows, setFieldRows] = useState([])
    const [submitting, setSubmitting] = useState(false)
    const [actionMessage, setActionMessage] = useState('')
    const [reprocessing, setReprocessing] = useState(false)
    const [deleting, setDeleting] = useState(false)
    const [bulkSelectedIds, setBulkSelectedIds] = useState(new Set())
    const [bulkProgress, setBulkProgress] = useState(null)

    useEffect(() => {
        const fields = selectedDocument?.extraction_result?.fields
        if (!fields || typeof fields !== 'object') {
            setFieldRows([])
            return
        }
        setFieldRows(
            Object.entries(fields)
                .filter(([, value]) => value !== '' && value !== null && value !== undefined)
                .map(([name, value]) => ({ name, value: formatEditableValue(value) })),
        )
    }, [selectedDocument?.id, selectedDocument?.extraction_result?.fields])

    const submitDecision = async (decision) => {
        if (!selectedDocumentId) {
            return
        }
        setSubmitting(true)
        try {
            await api.post(`/documents/${selectedDocumentId}/validate`, {
                decision,
                notes,
                corrected_fields: Object.fromEntries(
                    fieldRows
                        .filter((row) => row.name.trim())
                        .map((row) => [row.name.trim(), row.value]),
                ),
            })
            setNotes('')
            await onValidated()
        } finally {
            setSubmitting(false)
        }
    }

    const reprocessDocument = async () => {
        if (!selectedDocumentId || reprocessing) {
            return
        }
        setReprocessing(true)
        setActionMessage('')
        try {
            const response = await api.post(`/documents/${selectedDocumentId}/reprocess-ocr`)
            onDocumentUpdated(response.data)
            setActionMessage('Documento reprocessado.')
            await onValidated()
        } catch (requestError) {
            setActionMessage(readError(requestError, 'Falha ao reprocessar documento.'))
        } finally {
            setReprocessing(false)
        }
    }

    const deleteDocument = async () => {
        if (!selectedDocumentId || deleting) {
            return
        }
        const confirmed = window.confirm('Excluir este documento da aplicacao? O arquivo local sera preservado.')
        if (!confirmed) {
            return
        }
        setDeleting(true)
        setActionMessage('')
        try {
            await api.delete(`/documents/${selectedDocumentId}/delete`)
            onDocumentDeleted()
            await onValidated()
        } catch (requestError) {
            setActionMessage(readError(requestError, 'Falha ao excluir documento.'))
        } finally {
            setDeleting(false)
        }
    }

    const filteredValidationDocs = filterDocuments(documents, validationSearch)

    const bulkDelete = async () => {
        if (bulkSelectedIds.size === 0 || bulkProgress) return
        const ids = [...bulkSelectedIds]
        const confirmed = window.confirm(`Excluir ${ids.length} documento(s) selecionado(s)? Os arquivos locais serao preservados.`)
        if (!confirmed) return
        setBulkProgress({ action: 'delete', done: 0, total: ids.length })
        let failed = 0
        for (let i = 0; i < ids.length; i++) {
            try {
                await api.delete(`/documents/${ids[i]}/delete`)
            } catch {
                failed++
            }
            setBulkProgress({ action: 'delete', done: i + 1, total: ids.length })
        }
        setBulkProgress(null)
        setBulkSelectedIds(new Set())
        await onValidated()
        if (failed > 0) setActionMessage(`${failed} documento(s) nao puderam ser excluidos.`)
    }

    const bulkReprocess = async () => {
        if (bulkSelectedIds.size === 0 || bulkProgress) return
        const ids = [...bulkSelectedIds]
        setBulkProgress({ action: 'reprocess', done: 0, total: ids.length })
        let failed = 0
        for (let i = 0; i < ids.length; i++) {
            try {
                await api.post(`/documents/${ids[i]}/reprocess-ocr`)
            } catch {
                failed++
            }
            setBulkProgress({ action: 'reprocess', done: i + 1, total: ids.length })
        }
        setBulkProgress(null)
        setBulkSelectedIds(new Set())
        await onValidated()
        if (failed > 0) setActionMessage(`${failed} documento(s) nao puderam ser reprocessados.`)
    }

    return (
        <div className="grid gap-4 xl:grid-cols-[340px_minmax(360px,0.9fr)_minmax(460px,1.1fr)]">
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="flex flex-col gap-2 border-b border-zinc-200 px-4 py-3">
                    <div className="text-sm font-semibold">Fila de validacao</div>
                    <SearchInput value={validationSearch} onChange={(v) => { setValidationSearch(v); setBulkSelectedIds(new Set()) }} placeholder="Buscar..." />
                </div>
                {bulkSelectedIds.size > 0 ? (
                    <div className="flex flex-wrap items-center gap-2 border-b border-zinc-200 bg-zinc-50 px-3 py-2">
                        <span className="text-xs font-medium text-zinc-600">
                            {bulkProgress
                                ? bulkProgress.action === 'delete'
                                    ? `Excluindo ${bulkProgress.done}/${bulkProgress.total}...`
                                    : `Reprocessando ${bulkProgress.done}/${bulkProgress.total}...`
                                : `${bulkSelectedIds.size} selecionado(s)`}
                        </span>
                        <button
                            type="button"
                            disabled={!!bulkProgress}
                            onClick={bulkReprocess}
                            className="flex items-center gap-1 rounded border border-zinc-300 bg-white px-2 py-1 text-xs font-medium hover:bg-zinc-100 disabled:opacity-50"
                        >
                            <RefreshCw size={12} aria-hidden="true" />
                            Reprocessar
                        </button>
                        <button
                            type="button"
                            disabled={!!bulkProgress}
                            onClick={bulkDelete}
                            className="flex items-center gap-1 rounded border border-red-200 bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50"
                        >
                            <Trash2 size={12} aria-hidden="true" />
                            Excluir
                        </button>
                        <button
                            type="button"
                            disabled={!!bulkProgress}
                            onClick={() => setBulkSelectedIds(new Set())}
                            className="ml-auto text-xs text-zinc-400 hover:text-zinc-600 disabled:opacity-50"
                        >
                            Limpar selecao
                        </button>
                    </div>
                ) : null}
                <DocumentTable
                    documents={filteredValidationDocs}
                    selectedDocumentId={selectedDocumentId}
                    onSelectDocument={onSelectDocument}
                    compact
                    selectable
                    bulkSelectedIds={bulkSelectedIds}
                    onBulkSelectionChange={setBulkSelectedIds}
                />
            </section>
            <section className="min-h-[360px] rounded-md border border-zinc-200 bg-white">
                <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                    <div className="text-sm font-semibold">Documento</div>
                    {selectedDocument ? (
                        <a
                            href={`/api/ocr/documents/${selectedDocument.id}/file`}
                            target="_blank"
                            rel="noreferrer"
                            className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100"
                        >
                            Abrir
                        </a>
                    ) : null}
                </div>
                {!selectedDocument ? (
                    <EmptyState icon={FileText} text="Selecione um documento para visualizar." />
                ) : selectedDocument.content_type === 'application/pdf' ? (
                    <iframe
                        title="Documento selecionado"
                        src={`/api/ocr/documents/${selectedDocument.id}/file`}
                        className="h-[620px] w-full"
                    />
                ) : selectedDocument.content_type?.startsWith('image/') ? (
                    <div className="max-h-[620px] overflow-auto p-3">
                        <img src={`/api/ocr/documents/${selectedDocument.id}/file`} alt="Documento selecionado" className="max-w-full rounded border border-zinc-200" />
                    </div>
                ) : (
                    <EmptyState icon={FileText} text="Formato sem preview disponivel." />
                )}
            </section>
            <section className="min-h-[360px] rounded-md border border-zinc-200 bg-white p-4">
                {!selectedDocument ? (
                    <EmptyState icon={ClipboardCheck} text="Selecione um documento pendente." />
                ) : (
                    <div className="space-y-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                                <div className="text-sm font-semibold">{selectedDocument.original_filename || selectedDocument.id}</div>
                                <div className="mt-1 text-xs text-zinc-500">{selectedDocument.file_uri}</div>
                            </div>
                            <div className="flex flex-col items-end gap-2">
                                <OcrMetadataBadge metadata={selectedDocument.ocr_metadata} processing={reprocessing} />
                                <StatusBadge status={selectedDocument.status} />
                            </div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <button type="button" disabled={reprocessing || deleting} onClick={reprocessDocument} className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-100">
                                <RefreshCw size={16} aria-hidden="true" />
                                {reprocessing ? 'Reprocessando' : 'Reprocessar OCR'}
                            </button>
                            <button type="button" disabled={reprocessing || deleting} onClick={deleteDocument} className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100">
                                <Trash2 size={16} aria-hidden="true" />
                                {deleting ? 'Excluindo' : 'Excluir'}
                            </button>
                            {actionMessage ? <span className="text-sm text-zinc-600">{actionMessage}</span> : null}
                        </div>
                        <KeyValueGrid
                            values={{
                                schema: selectedDocument.extraction_result?.schema_id ?? '-',
                                confidence: selectedDocument.extraction_result?.confidence ?? '-',
                                layout: selectedDocument.layout || '-',
                            }}
                        />
                        {!selectedDocument.extraction_result ? (
                            <Alert>
                                Documento recebido. O OCR automatico ainda nao concluiu; use Atualizar em alguns instantes.
                            </Alert>
                        ) : null}
                        <ReadOnlyTranscription value={selectedDocument.full_transcription} />
                        <EditableFields rows={fieldRows} onChange={setFieldRows} />
                        <textarea
                            value={notes}
                            onChange={(event) => setNotes(event.target.value)}
                            className="input min-h-[86px]"
                            placeholder="Notas de validacao"
                        />
                        <div className="flex flex-wrap gap-2">
                            <button type="button" disabled={submitting} onClick={() => submitDecision('approved')} className="success-button">
                                <CheckCircle2 size={16} aria-hidden="true" />
                                Aprovar
                            </button>
                            <button type="button" disabled={submitting} onClick={() => submitDecision('rejected')} className="danger-button">
                                <XCircle size={16} aria-hidden="true" />
                                Rejeitar
                            </button>
                        </div>
                    </div>
                )}
            </section>
        </div>
    )
}

function EditableFields({ rows, onChange }) {
    const updateRow = (index, patch) => {
        onChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)))
    }

    const removeRow = (index) => {
        onChange(rows.filter((_, rowIndex) => rowIndex !== index))
    }

    return (
        <div className="rounded-md border border-zinc-200">
            <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                <div className="text-sm font-semibold">Campos extraidos</div>
                <button
                    type="button"
                    onClick={() => onChange([...rows, { name: '', value: '' }])}
                    className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100"
                >
                    Adicionar
                </button>
            </div>
            {rows.length === 0 ? (
                <div className="px-3 py-6 text-sm text-zinc-500">Nenhum campo extraido para editar.</div>
            ) : (
                <div className="divide-y divide-zinc-100">
                    {rows.map((row, index) => (
                        <div key={`${row.name}-${index}`} className="grid gap-2 px-3 py-3 md:grid-cols-[220px_1fr_auto]">
                            <input
                                value={row.name}
                                onChange={(event) => updateRow(index, { name: event.target.value })}
                                className="input"
                                placeholder="campo"
                            />
                            <input
                                value={row.value}
                                onChange={(event) => updateRow(index, { value: event.target.value })}
                                className="input"
                                placeholder="valor"
                            />
                            <button
                                type="button"
                                onClick={() => removeRow(index)}
                                className="h-9 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-600 hover:bg-zinc-100"
                            >
                                Remover
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

function OcrMetadataBadge({ metadata, processing = false }) {
    const engine = processing ? 'Reprocessando OCR' : (metadata?.engine_used || 'Aguardando OCR')
    const classification = processing ? 'reclassificando...' : (metadata?.classification || '-')
    const preprocessingHint = processing ? '-' : (metadata?.preprocessing_hint || '-')
    return (
        <div className="max-w-[360px] rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-right">
            <div className="text-xs font-semibold uppercase text-zinc-500">OCR utilizado</div>
            <div className="mt-1 text-sm font-semibold text-zinc-800">{engine}</div>
            <div className="mt-1 text-xs text-zinc-500">classificacao: {classification}</div>
            <div className="mt-1 break-words text-xs text-zinc-500">hint: {preprocessingHint}</div>
        </div>
    )
}

function ReadOnlyTranscription({ value }) {
    return (
        <div className="rounded-md border border-zinc-200">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">Transcricao completa</div>
            <textarea
                value={value || ''}
                readOnly
                className="min-h-[160px] w-full resize-y border-0 bg-zinc-50 px-3 py-3 text-sm leading-6 text-zinc-700 outline-none"
                placeholder="A transcricao aparecera aqui quando o OCR automatico concluir."
            />
        </div>
    )
}

const SETTINGS_TABS = [
    { id: 'setup', label: 'Modelo' },
    { id: 'ocr', label: 'OCR referencia' },
    { id: 'schema', label: 'Schema' },
    { id: 'instructions', label: 'Instrucoes' },
    { id: 'examples', label: 'Exemplos' },
    { id: 'test', label: 'Teste visual' },
    { id: 'rules', label: 'Regras' },
    { id: 'publish', label: 'Publicacao' },
]

const SETTINGS_AREAS = [
    { id: 'email', label: 'Email' },
    { id: 'whatsapp', label: 'WhatsApp' },
    { id: 'ocr-routing', label: 'OCR' },
    { id: 'extraction', label: 'Extracao' },
    { id: 'integrations', label: 'Integracoes' },
]

const SETTINGS_TAB_HELP = {
    setup: {
        title: 'Setup do modelo',
        text: 'Defina a identidade do template de extracao: nome, schema, tipo de documento, versao e status. Esses dados controlam qual configuracao sera aplicada apos OCR e classificacao.',
    },
    ocr: {
        title: 'OCR de referencia',
        text: 'Escolha um documento real ja processado para usar como base. Compare o original com a transcricao OCR e confirme se o texto tem qualidade suficiente para criar exemplos e regras.',
    },
    schema: {
        title: 'Schema de saida',
        text: 'Liste os campos que o LangExtract deve devolver. Para cada campo, informe tipo, obrigatoriedade e a regra de extracao ou normalizacao esperada.',
    },
    instructions: {
        title: 'Instrucoes LangExtract',
        text: 'Monte o prompt controlado que orienta a extracao. Use regras objetivas, proiba invencao de dados e exija rastreabilidade com o trecho fonte.',
    },
    examples: {
        title: 'Exemplos few-shot',
        text: 'Adicione exemplos revisados por humano. Cada linha deve ligar um campo ao valor correto e ao trecho OCR que justifica esse valor.',
    },
    test: {
        title: 'Teste visual',
        text: 'Use esta aba para validar o template com um documento real. Confira o original, o OCR destacado e o JSON esperado antes de publicar a versao.',
    },
    rules: {
        title: 'Regras de pos-processamento',
        text: 'Defina validacoes deterministicas aplicadas depois da extracao, como normalizacao de moeda/data e validacao de CPF ou CNPJ.',
    },
    publish: {
        title: 'Publicacao',
        text: 'Revise o JSON final do template, salve o schema e vincule o layout correspondente. Use status aprovado somente quando os testes estiverem conferidos.',
    },
}

const PROMPT_HINTS = [
    'Nao inventar dados',
    'Usar texto exato',
    'Normalizar datas',
    'Extrair valores monetarios',
    'Tratar multiplas ocorrencias',
    'Ignorar rodape/cabecalho',
    'Priorizar tabelas',
    'Priorizar campos proximos ao rotulo',
]

function SettingsView({ schemas, layouts, documents, onChanged }) {
    const [activeSettingsArea, setActiveSettingsArea] = useState('extraction')
    const [activeTab, setActiveTab] = useState('setup')
    const [schemaForm, setSchemaForm] = useState({
        tenant_slug: 'tenant-demo',
        schema_id: 'recibo_servico',
        version: 'v1',
        model_name: 'Recibo de servico',
        document_type: 'scanned_image',
        status: 'draft',
    })
    const [layoutForm, setLayoutForm] = useState({
        tenant_slug: 'tenant-demo',
        layout: 'recibo',
        document_type: 'scanned_image',
        schema_config_id: '',
        confidence_threshold: '0.75',
    })
    const [fields, setFields] = useState(DEFAULT_LANGEXTRACT_FIELDS)
    const [prompt, setPrompt] = useState(DEFAULT_LANGEXTRACT_PROMPT)
    const [normalizationRules, setNormalizationRules] = useState('{\n  "valor_total": { "type": "decimal", "required": true, "min": 0 },\n  "fornecedor_cnpj": { "type": "cnpj", "validate_checksum": true }\n}')
    const [examples, setExamples] = useState([
        {
            field: 'valor_total',
            expected: '120.00',
            source: 'Valor: 120,00',
        },
    ])
    const [referenceReview, setReferenceReview] = useState({
        quality: 'pending',
        action: 'review_before_examples',
        notes: '',
    })
    const [selectedDocumentId, setSelectedDocumentId] = useState('')
    const [referenceDocument, setReferenceDocument] = useState(null)
    const [testOutput, setTestOutput] = useState('{}')
    const [selectedSchemaId, setSelectedSchemaId] = useState('')
    // Track whether schema selection came from the user or auto-detection.
    const [schemaSelectionSource, setSchemaSelectionSource] = useState('auto')
    const [message, setMessage] = useState('')
    const [integrationSettings, setIntegrationSettings] = useState({
        tenant_slug: 'tenant-demo',
        approved_export_enabled: true,
        approved_export_dir: 'docuparse-project/exports/approved',
        approved_export_format: 'json',
        superlogica_base_url: '',
        superlogica_mode: 'disabled',
    })
    const [ocrSettings, setOcrSettings] = useState({
        tenant_slug: 'tenant-demo',
        digital_pdf_engine: 'docling',
        scanned_image_engine: 'openrouter',
        handwritten_engine: 'openrouter',
        technical_fallback_engine: 'tesseract',
        openrouter_model: '',
        openrouter_fallback_model: 'qwen/qwen2.5-vl-72b-instruct',
        timeout_seconds: 120,
        retry_empty_text_enabled: true,
        digital_pdf_min_text_blocks: 5,
    })
    const [emailSettings, setEmailSettings] = useState({
        tenant_slug: 'tenant-demo',
        provider: 'imap',
        inbox_folder: 'INBOX',
        imap_host: '',
        imap_port: 993,
        username: '',
        webhook_url: 'http://127.0.0.1:8070/api/v1/email/messages',
        accepted_content_types: 'application/pdf,image/jpeg,image/png,image/tiff,image/webp',
        max_attachment_mb: 20,
        blocked_senders: '',
        is_active: true,
    })

    // Cache the boleto default schema if it exists in the backend list.
    const boletoSchema = useMemo(
        () => schemas.find((schema) => schema.schema_id === BOLETO_DEFAULT_SCHEMA_ID),
        [schemas],
    )
    // Cache the nota fiscal default schema if it exists in the backend list.
    const notaFiscalSchema = useMemo(
        () => schemas.find((schema) => schema.schema_id === NOTA_FISCAL_DEFAULT_SCHEMA_ID),
        [schemas],
    )
    const contaAguaSchema = useMemo(
        () => schemas.find((schema) => schema.schema_id === CONTA_AGUA_DEFAULT_SCHEMA_ID),
        [schemas],
    )

    const activeLayout = layouts.find((layout) => (
        layout.schema_config_id === selectedSchemaId
        || (layout.layout === layoutForm.layout && layout.document_type === layoutForm.document_type)
    ))

    useEffect(() => {
        if (!selectedDocumentId) {
            setReferenceDocument(null)
            return
        }
        // Reset to auto so new documents can trigger default selection.
        setSchemaSelectionSource('auto')
        let ignore = false
        api.get(`/documents/${selectedDocumentId}`)
            .then((response) => {
                if (!ignore) {
                    setReferenceDocument(response.data)
                    setTestOutput(buildLangExtractPreview(response.data.full_transcription || '', fields))
                    const docType = response.data.document_type
                    if (docType) {
                        setSchemaForm((current) => ({ ...current, document_type: docType }))
                        setLayoutForm((current) => ({ ...current, document_type: docType }))
                    }
                }
            })
            .catch((requestError) => {
                if (!ignore) {
                    setMessage(readError(requestError, 'Nao foi possivel carregar o documento de referencia.'))
                }
            })
        return () => {
            ignore = true
        }
    }, [selectedDocumentId])

    // Auto-select BOLETO DEFAULT when OCR text indicates a boleto.
    useEffect(() => {
        const rawText = referenceDocument?.full_transcription || ''
        if (!rawText) {
            return
        }
        if (schemaSelectionSource === 'manual') {
            return
        }

        const isNotaFiscal = isLikelyNotaFiscalText(rawText)
        const isContaAgua = !isNotaFiscal && isLikelyContaAguaText(rawText)
        const isBoleto = !isNotaFiscal && !isContaAgua && isLikelyBoletoText(rawText)
        const detectedDocumentType = referenceDocument?.document_type || schemaForm.document_type

        if (isNotaFiscal) {
            const notaPrompt = notaFiscalPromptForDocumentType(detectedDocumentType)
            if (notaFiscalSchema) {
                loadExistingSchema(notaFiscalSchema.id, { source: 'auto' })
                setFields(NOTA_FISCAL_DEFAULT_FIELDS)
                setExamples(NOTA_FISCAL_DEFAULT_EXAMPLES)
                setNormalizationRules(JSON.stringify(NOTA_FISCAL_DEFAULT_RULES, null, 2))
                setSchemaForm((current) => ({
                    ...current,
                    model_name: NOTA_FISCAL_DEFAULT_MODEL_NAME,
                    schema_id: NOTA_FISCAL_DEFAULT_SCHEMA_ID,
                    document_type: detectedDocumentType,
                }))
                setPrompt(notaPrompt)
                return
            }
            setSelectedSchemaId('')
            setSchemaForm((current) => ({
                ...current,
                model_name: NOTA_FISCAL_DEFAULT_MODEL_NAME,
                schema_id: NOTA_FISCAL_DEFAULT_SCHEMA_ID,
                document_type: detectedDocumentType,
            }))
            setFields(NOTA_FISCAL_DEFAULT_FIELDS)
            setPrompt(notaPrompt)
            setExamples(NOTA_FISCAL_DEFAULT_EXAMPLES)
            setNormalizationRules(JSON.stringify(NOTA_FISCAL_DEFAULT_RULES, null, 2))
            return
        }

        if (isContaAgua) {
            const aguaPrompt = contaAguaPromptForDocumentType(detectedDocumentType)
            if (contaAguaSchema) {
                loadExistingSchema(contaAguaSchema.id, { source: 'auto' })
                setFields(CONTA_AGUA_DEFAULT_FIELDS)
                setExamples(CONTA_AGUA_DEFAULT_EXAMPLES)
                setNormalizationRules(JSON.stringify(CONTA_AGUA_DEFAULT_RULES, null, 2))
                setSchemaForm((current) => ({
                    ...current,
                    model_name: CONTA_AGUA_DEFAULT_MODEL_NAME,
                    schema_id: CONTA_AGUA_DEFAULT_SCHEMA_ID,
                    document_type: detectedDocumentType,
                }))
                setPrompt(aguaPrompt)
                return
            }
            setSelectedSchemaId('')
            setSchemaForm((current) => ({
                ...current,
                model_name: CONTA_AGUA_DEFAULT_MODEL_NAME,
                schema_id: CONTA_AGUA_DEFAULT_SCHEMA_ID,
                document_type: detectedDocumentType,
            }))
            setFields(CONTA_AGUA_DEFAULT_FIELDS)
            setPrompt(aguaPrompt)
            setExamples(CONTA_AGUA_DEFAULT_EXAMPLES)
            setNormalizationRules(JSON.stringify(CONTA_AGUA_DEFAULT_RULES, null, 2))
            return
        }

        if (!isBoleto) {
            if ([BOLETO_DEFAULT_SCHEMA_ID, NOTA_FISCAL_DEFAULT_SCHEMA_ID, CONTA_AGUA_DEFAULT_SCHEMA_ID].includes(schemaForm.schema_id)) {
                setSelectedSchemaId('')
                setSchemaForm((current) => ({
                    ...current,
                    model_name: DEFAULT_MODEL_NAME,
                    schema_id: DEFAULT_SCHEMA_ID,
                }))
                setFields(DEFAULT_LANGEXTRACT_FIELDS)
                setPrompt(DEFAULT_LANGEXTRACT_PROMPT)
                setExamples([])
            }
            return
        }
        const boletoPrompt = boletoPromptForDocumentType(detectedDocumentType)

        if (boletoSchema) {
            loadExistingSchema(boletoSchema.id, { source: 'auto' })
            setFields(BOLETO_DEFAULT_FIELDS)
            setExamples(BOLETO_DEFAULT_EXAMPLES)
            setNormalizationRules(JSON.stringify(BOLETO_DEFAULT_RULES, null, 2))
            setSchemaForm((current) => ({
                ...current,
                model_name: BOLETO_DEFAULT_MODEL_NAME,
                schema_id: BOLETO_DEFAULT_SCHEMA_ID,
                document_type: detectedDocumentType,
            }))
            setPrompt(boletoPrompt)
            return
        }

        setSelectedSchemaId('')
        setSchemaForm((current) => ({
            ...current,
            model_name: BOLETO_DEFAULT_MODEL_NAME,
            schema_id: BOLETO_DEFAULT_SCHEMA_ID,
            document_type: detectedDocumentType,
        }))
        setFields(BOLETO_DEFAULT_FIELDS)
        setPrompt(boletoPrompt)
        setExamples(BOLETO_DEFAULT_EXAMPLES)
        setNormalizationRules(JSON.stringify(BOLETO_DEFAULT_RULES, null, 2))
    }, [
        referenceDocument?.id,
        referenceDocument?.full_transcription,
        referenceDocument?.document_type,
        boletoSchema,
        notaFiscalSchema,
        contaAguaSchema,
        schemaSelectionSource,
    ])

    // Keep the boleto prompt aligned with the detected document type.
    useEffect(() => {
        if (schemaForm.schema_id !== BOLETO_DEFAULT_SCHEMA_ID) {
            return
        }
        const boletoPrompt = boletoPromptForDocumentType(schemaForm.document_type)
        if (prompt !== boletoPrompt) {
            setPrompt(boletoPrompt)
        }
    }, [schemaForm.schema_id, schemaForm.document_type])

    // Keep the nota fiscal prompt aligned with the detected document type.
    useEffect(() => {
        if (schemaForm.schema_id !== NOTA_FISCAL_DEFAULT_SCHEMA_ID) {
            return
        }
        const notaPrompt = notaFiscalPromptForDocumentType(schemaForm.document_type)
        if (prompt !== notaPrompt) {
            setPrompt(notaPrompt)
        }
    }, [schemaForm.schema_id, schemaForm.document_type])

    // Keep the conta de agua prompt aligned with the detected document type.
    useEffect(() => {
        if (schemaForm.schema_id !== CONTA_AGUA_DEFAULT_SCHEMA_ID) {
            return
        }
        const aguaPrompt = contaAguaPromptForDocumentType(schemaForm.document_type)
        if (prompt !== aguaPrompt) {
            setPrompt(aguaPrompt)
        }
    }, [schemaForm.schema_id, schemaForm.document_type])

    useEffect(() => {
        let ignore = false
        api.get('/settings/integrations', { params: { tenant: integrationSettings.tenant_slug } })
            .then((response) => {
                if (!ignore) {
                    setIntegrationSettings((current) => ({
                        ...current,
                        ...response.data,
                    }))
                }
            })
            .catch((requestError) => {
                if (!ignore) {
                    setMessage(readError(requestError, 'Nao foi possivel carregar configuracoes de integracao.'))
                }
            })
        return () => {
            ignore = true
        }
    }, [])

    useEffect(() => {
        let ignore = false
        api.get('/settings/ocr', { params: { tenant: ocrSettings.tenant_slug } })
            .then((response) => {
                if (!ignore) {
                    setOcrSettings((current) => ({
                        ...current,
                        ...response.data,
                    }))
                }
            })
            .catch((requestError) => {
                if (!ignore) {
                    setMessage(readError(requestError, 'Nao foi possivel carregar configuracoes de OCR.'))
                }
            })
        return () => {
            ignore = true
        }
    }, [])

    useEffect(() => {
        let ignore = false
        api.get('/settings/email', { params: { tenant: emailSettings.tenant_slug } })
            .then((response) => {
                if (!ignore) {
                    setEmailSettings((current) => ({
                        ...current,
                        ...response.data,
                    }))
                }
            })
            .catch((requestError) => {
                if (!ignore) {
                    setMessage(readError(requestError, 'Nao foi possivel carregar configuracoes de email.'))
                }
            })
        return () => {
            ignore = true
        }
    }, [])

    const schemaDefinition = useMemo(() => buildLangExtractDefinition({
        schemaForm,
        fields,
        prompt,
        examples,
        normalizationRules,
        referenceReview,
        referenceDocument,
    }), [schemaForm, fields, prompt, examples, normalizationRules, referenceReview, referenceDocument])

    const loadExistingSchema = (schemaId, { source = 'manual' } = {}) => {
        // Preserve the selection source so auto-detection does not override manual choices.
        setSchemaSelectionSource(source)
        setSelectedSchemaId(schemaId)
        const schema = schemas.find((item) => item.id === schemaId)
        if (!schema) {
            return
        }
        const definition = schema.definition || {}
        setSchemaForm((current) => ({
            ...current,
            schema_id: schema.schema_id,
            version: schema.version,
            model_name: definition.model_name || schema.schema_id,
            document_type: definition.document_type || current.document_type,
            status: definition.status || current.status,
        }))
        const linkedLayout = layouts.find((layout) => layout.schema_config_id === schema.id)
        if (linkedLayout) {
            setLayoutForm((current) => ({
                ...current,
                layout: linkedLayout.layout,
                document_type: linkedLayout.document_type,
                schema_config_id: schema.id,
                confidence_threshold: String(linkedLayout.confidence_threshold ?? current.confidence_threshold),
            }))
        } else {
            setLayoutForm((current) => ({
                ...current,
                schema_config_id: schema.id,
                document_type: definition.document_type || current.document_type,
            }))
        }
        if (Array.isArray(definition.fields)) {
            setFields(definition.fields.map((field) => ({
                name: field.name || '',
                type: field.type || 'string',
                required: Boolean(field.required),
                rule: field.rule || '',
            })))
        }
        if (definition.prompt?.instructions) {
            setPrompt(definition.prompt.instructions)
        }
        if (Array.isArray(definition.examples)) {
            setExamples(definition.examples)
        }
        if (definition.post_processing) {
            setNormalizationRules(JSON.stringify(definition.post_processing, null, 2))
        }
        if (definition.reference_review) {
            setReferenceReview({
                quality: definition.reference_review.ocr_quality || 'pending',
                action: definition.reference_review.recommended_action || 'review_before_examples',
                notes: definition.reference_review.notes || '',
            })
        }
        setMessage(`Schema carregado: ${schema.schema_id} ${schema.version}`)
    }

    const createSchema = async () => {
        setMessage('')
        try {
            const payload = {
                tenant_slug: schemaForm.tenant_slug,
                schema_id: schemaForm.schema_id,
                version: schemaForm.version,
                definition: schemaDefinition,
                is_active: schemaForm.status !== 'disabled',
            }
            const response = selectedSchemaId
                ? await api.patch(`/schema-configs/${selectedSchemaId}`, payload)
                : await api.post('/schema-configs', payload)
            setSelectedSchemaId(response.data.id)
            setMessage('Modelo LangExtract salvo como schema.')
            await onChanged()
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao criar schema.'))
        }
    }

    const saveDraft = async () => {
        setMessage('')
        try {
            const draftDefinition = {
                ...schemaDefinition,
                status: 'draft',
            }
            const payload = {
                tenant_slug: schemaForm.tenant_slug,
                schema_id: schemaForm.schema_id,
                version: schemaForm.version,
                definition: draftDefinition,
                is_active: true,
            }
            const response = selectedSchemaId
                ? await api.patch(`/schema-configs/${selectedSchemaId}`, payload)
                : await api.post('/schema-configs', payload)
            setSelectedSchemaId(response.data.id)
            setSchemaForm((current) => ({ ...current, status: 'draft' }))
            setMessage('Rascunho salvo.')
            await onChanged()
            return true
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao salvar rascunho.'))
            return false
        }
    }

    const goToNextStep = async () => {
        const saved = await saveDraft()
        if (!saved) {
            return
        }
        const currentIndex = SETTINGS_TABS.findIndex((tab) => tab.id === activeTab)
        const nextTab = SETTINGS_TABS[currentIndex + 1]
        if (nextTab) {
            setActiveTab(nextTab.id)
        }
    }

    const createLayout = async () => {
        setMessage('')
        try {
            await api.post('/layout-configs', {
                tenant_slug: layoutForm.tenant_slug,
                layout: layoutForm.layout,
                document_type: layoutForm.document_type,
                schema_config_id: layoutForm.schema_config_id,
                confidence_threshold: Number(layoutForm.confidence_threshold),
            })
            setLayoutForm((current) => ({ ...current, layout: '' }))
            setMessage('Layout criado.')
            await onChanged()
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao criar layout.'))
        }
    }

    const saveIntegrationSettings = async () => {
        setMessage('')
        try {
            const response = await api.patch('/settings/integrations', integrationSettings)
            setIntegrationSettings((current) => ({ ...current, ...response.data }))
            setMessage('Configuracoes de integracao salvas.')
            await onChanged()
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao salvar configuracoes de integracao.'))
        }
    }

    const saveOcrSettings = async () => {
        setMessage('')
        try {
            const payload = {
                ...ocrSettings,
                timeout_seconds: Number(ocrSettings.timeout_seconds) || 120,
                digital_pdf_min_text_blocks: Number(ocrSettings.digital_pdf_min_text_blocks) || 5,
            }
            const response = await api.patch('/settings/ocr', payload)
            setOcrSettings((current) => ({ ...current, ...response.data }))
            setMessage('Configuracoes de OCR salvas.')
            await onChanged()
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao salvar configuracoes de OCR.'))
        }
    }

    const saveEmailSettings = async () => {
        setMessage('')
        try {
            const payload = {
                ...emailSettings,
                imap_port: Number(emailSettings.imap_port) || 993,
                max_attachment_mb: Number(emailSettings.max_attachment_mb) || 20,
            }
            const response = await api.patch('/settings/email', payload)
            setEmailSettings((current) => ({ ...current, ...response.data }))
            setMessage('Configuracoes de email salvas.')
            await onChanged()
            return true
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao salvar configuracoes de email.'))
            return false
        }
    }

    const testEmailPoll = async () => {
        setMessage('')
        if (emailSettings.provider === 'imap') {
            if (!emailSettings.imap_host?.trim()) {
                setMessage('Preencha o campo "Host IMAP" antes de testar (ex: imap.gmail.com).')
                return
            }
            if (!emailSettings.username?.trim()) {
                setMessage('Preencha o campo "Usuario" com o endereco de email monitorado.')
                return
            }
        }
        try {
            const saved = await saveEmailSettings()
            if (!saved) {
                return
            }
            const response = await comApi.post('/email/poll', null, {
                params: { tenant_id: emailSettings.tenant_slug || 'tenant-demo' },
            })
            const imported = response.data.accepted_count || 0
            const duplicates = response.data.duplicate_count || 0
            let pollMsg = `Captura IMAP executada: ${imported} documento(s) importado(s).`
            if (duplicates > 0) {
                pollMsg += ` ${duplicates} já existia(m) no sistema e foi(ram) ignorado(s).`
            }
            setMessage(pollMsg)
            await onChanged()
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao executar captura IMAP.'))
        }
    }

    return (
        <div className="space-y-4">
            {message ? <Alert>{message}</Alert> : null}
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="flex gap-1 overflow-x-auto border-b border-zinc-200 px-3 py-2">
                    {SETTINGS_AREAS.map((area) => (
                        <button
                            key={area.id}
                            type="button"
                            onClick={() => setActiveSettingsArea(area.id)}
                            className={`h-9 shrink-0 rounded-md px-3 text-sm font-medium ${activeSettingsArea === area.id ? 'bg-zinc-900 text-white' : 'text-zinc-600 hover:bg-zinc-100'}`}
                        >
                            {area.label}
                        </button>
                    ))}
                </div>
                {activeSettingsArea === 'extraction' ? (
                    <>
                <div className="flex gap-1 overflow-x-auto border-b border-zinc-200 px-3 py-2">
                    {SETTINGS_TABS.map((tab) => (
                        <button
                            key={tab.id}
                            type="button"
                            onClick={() => setActiveTab(tab.id)}
                            className={`h-9 shrink-0 rounded-md px-3 text-sm font-medium ${activeTab === tab.id ? 'bg-zinc-900 text-white' : 'text-zinc-600 hover:bg-zinc-100'}`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
                <div className="p-4">
                    <TabHelp tab={activeTab} />
                    {activeTab !== 'setup' ? (
                        <ActiveTemplateHeader schemaForm={schemaForm} layoutForm={layoutForm} activeLayout={activeLayout} onChangeModel={() => setActiveTab('setup')} />
                    ) : null}
                    {activeTab === 'setup' ? (
                        <div className="space-y-4">
                            <section className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
                                <div className="grid gap-3 lg:grid-cols-[minmax(260px,1fr)_220px]">
                                    <Field label="Selecionar modelo existente">
                                        <select
                                            value={selectedSchemaId}
                                            onChange={(event) => loadExistingSchema(event.target.value, { source: 'manual' })}
                                            className="input"
                                        >
                                            <option value="">Criar novo modelo</option>
                                            {schemas.map((schema) => (
                                                <option key={schema.id} value={schema.id}>
                                                    {schema.schema_id} {schema.version}
                                                </option>
                                            ))}
                                        </select>
                                    </Field>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setSelectedSchemaId('')
                                            setSchemaForm({
                                                tenant_slug: 'tenant-demo',
                                                schema_id: 'novo_modelo',
                                                version: 'v1',
                                                model_name: 'Novo modelo',
                                                document_type: 'scanned_image',
                                                status: 'draft',
                                            })
                                            setLayoutForm({
                                                tenant_slug: 'tenant-demo',
                                                layout: 'novo_layout',
                                                document_type: 'scanned_image',
                                                schema_config_id: '',
                                                confidence_threshold: '0.75',
                                            })
                                            setFields(DEFAULT_LANGEXTRACT_FIELDS)
                                            setPrompt(DEFAULT_LANGEXTRACT_PROMPT)
                                            setExamples([])
                                            setReferenceReview({ quality: 'pending', action: 'review_before_examples', notes: '' })
                                        }}
                                        className="mt-6 h-9 rounded-md border border-zinc-300 px-3 text-sm font-medium hover:bg-zinc-100"
                                    >
                                        Novo modelo
                                    </button>
                                </div>
                            </section>
                            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
                                <div className="grid gap-3 md:grid-cols-2">
                                    <Field label="Nome do modelo">
                                        <input value={schemaForm.model_name} onChange={(event) => setSchemaForm({ ...schemaForm, model_name: event.target.value })} className="input" placeholder="Recibo de servico" />
                                    </Field>
                                    <Field label="Schema">
                                        <input value={schemaForm.schema_id} onChange={(event) => setSchemaForm({ ...schemaForm, schema_id: event.target.value })} className="input" placeholder="recibo_servico" />
                                    </Field>
                                    <Field label="Tenant">
                                        <input value={schemaForm.tenant_slug} onChange={(event) => setSchemaForm({ ...schemaForm, tenant_slug: event.target.value, })} className="input" />
                                    </Field>
                                    <Field label="Versao">
                                        <input value={schemaForm.version} onChange={(event) => setSchemaForm({ ...schemaForm, version: event.target.value })} className="input" />
                                    </Field>
                                    <Field label="Tipo de documento">
                                        <select value={schemaForm.document_type} onChange={(event) => {
                                            setSchemaForm({ ...schemaForm, document_type: event.target.value })
                                            setLayoutForm({ ...layoutForm, document_type: event.target.value })
                                        }} className="input">
                                            <option value="scanned_image">Imagem/PDF escaneado</option>
                                            <option value="digital_pdf">PDF textual</option>
                                            <option value="handwritten_complex">Manuscrito complexo</option>
                                        </select>
                                    </Field>
                                    <Field label="Status">
                                        <select value={schemaForm.status} onChange={(event) => setSchemaForm({ ...schemaForm, status: event.target.value })} className="input">
                                            <option value="draft">Rascunho</option>
                                            <option value="testing">Em teste</option>
                                            <option value="approved">Aprovado</option>
                                            <option value="disabled">Desativado</option>
                                        </select>
                                    </Field>
                                </div>
                                <HintPanel
                                    title="Checklist LangExtract"
                                    items={[
                                        'Defina o schema antes do prompt.',
                                        'Use exemplos anotados para campos ambiguos.',
                                        'Mantenha o trecho fonte para validacao visual.',
                                        'Publique somente versoes testadas.',
                                    ]}
                                />
                            </div>
                            <div className="grid gap-4 lg:grid-cols-2">
                                <ConfigList title="Schemas existentes" items={schemas} primaryKey="schema_id" secondaryKey="version" />
                                <ConfigList title="Layouts existentes" items={layouts} primaryKey="layout" secondaryKey="document_type" />
                            </div>
                        </div>
                    ) : null}

                    {activeTab === 'ocr' ? (
                        <ReferenceDocumentPanel
                            documents={documents}
                            selectedDocumentId={selectedDocumentId}
                            onSelectDocument={setSelectedDocumentId}
                            referenceDocument={referenceDocument}
                            fields={fields}
                            review={referenceReview}
                            onReviewChange={setReferenceReview}
                        />
                    ) : null}

                    {activeTab === 'schema' ? (
                        <SchemaFieldsEditor
                            fields={fields}
                            onChange={setFields}
                            schemaForm={schemaForm}
                        />
                    ) : null}

                    {activeTab === 'instructions' ? (
                        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                            <Field label="Prompt controlado">
                                <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} className="input min-h-[280px] font-mono" />
                            </Field>
                            <HintPanel title="Blocos prontos" items={PROMPT_HINTS} onUse={(hint) => setPrompt((current) => `${current}\n- ${hint}.`)} />
                        </div>
                    ) : null}

                    {activeTab === 'examples' ? (
                        <ExamplesEditor examples={examples} onChange={setExamples} referenceText={referenceDocument?.full_transcription || ''} />
                    ) : null}

                    {activeTab === 'test' ? (
                        <div className="grid gap-4 xl:grid-cols-[minmax(320px,0.9fr)_minmax(360px,1.1fr)_minmax(320px,0.8fr)]">
                            <DocumentPreview document={referenceDocument} />
                            <HighlightedOcrText text={referenceDocument?.full_transcription || ''} fields={fields} examples={examples} />
                            <Field label="Preview JSON">
                                <textarea value={testOutput} onChange={(event) => setTestOutput(event.target.value)} className="input min-h-[520px] font-mono" />
                            </Field>
                        </div>
                    ) : null}

                    {activeTab === 'rules' ? (
                        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                            <Field label="Regras de pos-processamento JSON">
                                <textarea value={normalizationRules} onChange={(event) => setNormalizationRules(event.target.value)} className="input min-h-[300px] font-mono" />
                            </Field>
                            <HintPanel
                                title="Regras recomendadas"
                                items={[
                                    'Normalizar moeda para decimal.',
                                    'Normalizar datas para YYYY-MM-DD.',
                                    'Validar CPF/CNPJ por checksum.',
                                    'Comparar valor liquido com total quando houver.',
                                ]}
                            />
                        </div>
                    ) : null}

                    {activeTab === 'publish' ? (
                        <div className="grid gap-4 xl:grid-cols-2">
                            <section className="rounded-md border border-zinc-200 p-4">
                                <div className="mb-3 text-sm font-semibold">Salvar modelo como schema</div>
                                <pre className="max-h-[360px] overflow-auto rounded-md bg-zinc-950 p-3 text-xs text-zinc-50">{JSON.stringify(schemaDefinition, null, 2)}</pre>
                                <button type="button" onClick={createSchema} disabled={!schemaForm.schema_id.trim()} className="primary-button mt-3">
                                    Salvar schema LangExtract
                                </button>
                            </section>
                            <section className="rounded-md border border-zinc-200 p-4">
                                <div className="mb-3 text-sm font-semibold">Vincular layout ao schema</div>
                                <div className="grid gap-3 md:grid-cols-2">
                                    <Field label="Layout">
                                        <input value={layoutForm.layout} onChange={(event) => setLayoutForm({ ...layoutForm, layout: event.target.value })} className="input" />
                                    </Field>
                                    <Field label="Tipo documento">
                                        <input value={layoutForm.document_type} onChange={(event) => setLayoutForm({ ...layoutForm, document_type: event.target.value })} className="input" />
                                    </Field>
                                    <Field label="Schema">
                                        <select value={layoutForm.schema_config_id} onChange={(event) => setLayoutForm({ ...layoutForm, schema_config_id: event.target.value })} className="input">
                                            <option value="">Selecionar</option>
                                            {schemas.map((schema) => (
                                                <option key={schema.id} value={schema.id}>
                                                    {schema.schema_id} {schema.version}
                                                </option>
                                            ))}
                                        </select>
                                    </Field>
                                    <Field label="Confianca minima">
                                        <input value={layoutForm.confidence_threshold} onChange={(event) => setLayoutForm({ ...layoutForm, confidence_threshold: event.target.value })} className="input" />
                                    </Field>
                                </div>
                                <button type="button" onClick={createLayout} disabled={!layoutForm.layout.trim() || !layoutForm.schema_config_id} className="primary-button mt-3">
                                    Criar layout
                                </button>
                            </section>
                        </div>
                    ) : null}
                    {activeTab !== 'publish' ? (
                        <SettingsStepActions
                            activeTab={activeTab}
                            onSaveDraft={saveDraft}
                            onNext={goToNextStep}
                        />
                    ) : null}
                </div>
                    </>
                ) : null}
                {activeSettingsArea === 'ocr-routing' ? (
                    <OcrSettingsPanel
                        settings={ocrSettings}
                        onChange={setOcrSettings}
                        onSave={saveOcrSettings}
                    />
                ) : null}
                {activeSettingsArea === 'email' ? (
                    <EmailSettingsPanel
                        settings={emailSettings}
                        onChange={setEmailSettings}
                        onSave={saveEmailSettings}
                        onPoll={testEmailPoll}
                    />
                ) : null}
                {activeSettingsArea === 'whatsapp' ? <WhatsAppSettingsPanel /> : null}
                {activeSettingsArea === 'integrations' ? (
                    <IntegrationSettingsPanel
                        settings={integrationSettings}
                        onChange={setIntegrationSettings}
                        onSave={saveIntegrationSettings}
                    />
                ) : null}
            </section>
        </div>
    )
}

function TabHelp({ tab }) {
    const help = SETTINGS_TAB_HELP[tab]
    if (!help) {
        return null
    }
    return (
        <div className="mb-4 rounded-md border border-sky-200 bg-sky-50 px-4 py-3">
            <div className="text-sm font-semibold text-sky-950">{help.title}</div>
            <div className="mt-1 text-sm leading-6 text-sky-800">{help.text}</div>
        </div>
    )
}

function OcrSettingsPanel({ settings, onChange, onSave }) {
    const updateField = (field, value) => {
        onChange((current) => ({ ...current, [field]: value }))
    }

    const activeOcrRoutes = [
        {
            type: 'PDF textual',
            classification: 'digital_pdf',
            engine: engineLabel(settings.digital_pdf_engine),
            detail: 'Usado quando o classificador encontra blocos de texto suficientes no PDF.',
        },
        {
            type: 'Imagem/PDF escaneado',
            classification: 'scanned_image',
            engine: engineLabel(settings.scanned_image_engine),
            detail: 'Usado para documentos sem camada textual confiavel, incluindo fotos e PDFs imagem.',
        },
        {
            type: 'Manuscrito complexo',
            classification: 'handwritten_complex',
            engine: engineLabel(settings.handwritten_engine),
            detail: 'Usado para documentos com escrita manual ou baixa estrutura textual.',
        },
        {
            type: 'Fallback tecnico',
            classification: 'fallback',
            engine: engineLabel(settings.technical_fallback_engine),
            detail: 'Usado apenas quando o engine primario falha antes de retornar transcricao.',
        },
    ]

    return (
        <div className="space-y-4 p-4">
            <ConfigIntro
                title="OCR"
                text="Perfil operacional atual do OCR. A tela mostra somente os engines usados de fato no fluxo automatico: Docling para PDF textual, OpenRouter para imagem/PDF escaneado e Tesseract como fallback tecnico."
            />
            <div className="flex justify-end">
                <button type="button" onClick={onSave} className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700">
                    <CheckCircle2 size={16} aria-hidden="true" />
                    Salvar OCR
                </button>
            </div>
            <div className="grid gap-4 xl:grid-cols-2">
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Roteamento ativo</div>
                    <div className="space-y-3">
                        {activeOcrRoutes.map((route) => (
                            <div key={route.classification} className="rounded-md border border-zinc-200 bg-zinc-50 p-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div>
                                        <div className="text-sm font-semibold">{route.type}</div>
                                        <div className="mt-1 text-xs text-zinc-500">{route.classification}</div>
                                    </div>
                                    <span className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs font-semibold text-zinc-700">
                                        {route.engine}
                                    </span>
                                </div>
                                <p className="mt-2 text-sm leading-6 text-zinc-600">{route.detail}</p>
                            </div>
                        ))}
                    </div>
                </section>
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Configuracao em uso</div>
                    <div className="grid gap-3 md:grid-cols-2">
                        <Field label="PDF textual">
                            <EngineSelect value={settings.digital_pdf_engine} onChange={(value) => updateField('digital_pdf_engine', value)} />
                        </Field>
                        <Field label="Imagem/PDF escaneado">
                            <EngineSelect value={settings.scanned_image_engine} onChange={(value) => updateField('scanned_image_engine', value)} />
                        </Field>
                        <Field label="Manuscrito complexo">
                            <EngineSelect value={settings.handwritten_engine} onChange={(value) => updateField('handwritten_engine', value)} />
                        </Field>
                        <Field label="Fallback tecnico">
                            <EngineSelect value={settings.technical_fallback_engine} onChange={(value) => updateField('technical_fallback_engine', value)} />
                        </Field>
                        <Field label="Modelo OpenRouter primario">
                            <input
                                className="input"
                                value={settings.openrouter_model || ''}
                                onChange={(event) => updateField('openrouter_model', event.target.value)}
                                placeholder="Vazio usa OPENROUTER_MODEL do .env"
                            />
                        </Field>
                        <Field label="Modelo OpenRouter secundario">
                            <input
                                className="input"
                                value={settings.openrouter_fallback_model || ''}
                                onChange={(event) => updateField('openrouter_fallback_model', event.target.value)}
                                placeholder="qwen/qwen2.5-vl-72b-instruct"
                            />
                        </Field>
                        <Field label="Timeout segundos">
                            <input
                                className="input"
                                type="number"
                                min="10"
                                max="600"
                                value={settings.timeout_seconds}
                                onChange={(event) => updateField('timeout_seconds', event.target.value)}
                            />
                        </Field>
                        <Field label="Fallback se texto vazio">
                            <select
                                className="input"
                                value={settings.retry_empty_text_enabled ? 'enabled' : 'disabled'}
                                onChange={(event) => updateField('retry_empty_text_enabled', event.target.value === 'enabled')}
                            >
                                <option value="enabled">Tentar segundo modelo</option>
                                <option value="disabled">Nao tentar</option>
                            </select>
                        </Field>
                        <Field label="Minimo de blocos de texto PDF">
                            <input
                                className="input"
                                type="number"
                                min="1"
                                max="200"
                                value={settings.digital_pdf_min_text_blocks}
                                onChange={(event) => updateField('digital_pdf_min_text_blocks', event.target.value)}
                            />
                        </Field>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-zinc-500">
                        A chave OpenRouter continua no `.env` e nao e gravada aqui. PaddleOCR, EasyOCR, TrOCR, LlamaParse e DeepSeek permanecem como codigo legado/opcional, mas nao fazem parte do setup operacional atual.
                    </p>
                </section>
            </div>
        </div>
    )
}

function EngineSelect({ value, onChange }) {
    return (
        <select className="input" value={value || 'docling'} onChange={(event) => onChange(event.target.value)}>
            <option value="docling">Docling</option>
            <option value="openrouter">OpenRouter</option>
            <option value="tesseract">Tesseract</option>
        </select>
    )
}

function engineLabel(value) {
    return {
        docling: 'Docling',
        openrouter: 'OpenRouter',
        tesseract: 'Tesseract',
    }[value] || value || '-'
}

function EmailSettingsPanel({ settings, onChange, onSave, onPoll }) {
    const updateField = (field, value) => {
        onChange((current) => ({ ...current, [field]: value }))
    }

    return (
        <div className="space-y-4 p-4">
            <ConfigIntro
                title="Email"
                text="Configure como documentos chegam por email. A senha/app password continua fora do banco e deve estar em DOCUPARSE_IMAP_PASSWORD no servidor."
            />
            <div className="flex flex-wrap justify-end gap-2">
                <button type="button" onClick={onPoll} className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100">
                    <RefreshCw size={16} aria-hidden="true" />
                    Testar captura IMAP
                </button>
                <button type="button" onClick={onSave} className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700">
                    <CheckCircle2 size={16} aria-hidden="true" />
                    Salvar email
                </button>
            </div>
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Conta de captura</div>
                    <div className="grid gap-3 md:grid-cols-2">
                        <Field label="Provider">
                            <select className="input" value={settings.provider || 'imap'} onChange={(event) => updateField('provider', event.target.value)}>
                                <option value="imap">IMAP</option>
                                <option value="webhook">Webhook</option>
                                <option value="manual_test">Teste manual</option>
                            </select>
                        </Field>
                        <Field label="Ativo">
                            <select className="input" value={settings.is_active ? 'enabled' : 'disabled'} onChange={(event) => updateField('is_active', event.target.value === 'enabled')}>
                                <option value="enabled">Ativo</option>
                                <option value="disabled">Inativo</option>
                            </select>
                        </Field>
                        <Field label="Pasta monitorada">
                            <input className="input" value={settings.inbox_folder || ''} onChange={(event) => updateField('inbox_folder', event.target.value)} />
                        </Field>
                        <Field label="Host IMAP">
                            <input className="input" value={settings.imap_host || ''} onChange={(event) => updateField('imap_host', event.target.value)} placeholder="imap.exemplo.com" />
                        </Field>
                        <Field label="Porta">
                            <input className="input" type="number" min="1" max="65535" value={settings.imap_port} onChange={(event) => updateField('imap_port', event.target.value)} />
                        </Field>
                        <Field label="Usuario">
                            <input className="input" value={settings.username || ''} onChange={(event) => updateField('username', event.target.value)} placeholder="documentos@empresa.com" />
                        </Field>
                        <Field label="Senha/app password">
                            <input className="input" type="password" placeholder="Nao persistido por enquanto" disabled />
                        </Field>
                        <Field label="Webhook URL">
                            <input className="input" value={settings.webhook_url || ''} onChange={(event) => updateField('webhook_url', event.target.value)} />
                        </Field>
                    </div>
                </section>
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Regras de anexos</div>
                    <div className="space-y-3">
                        <Field label="Tipos aceitos">
                            <input className="input" value={settings.accepted_content_types || ''} onChange={(event) => updateField('accepted_content_types', event.target.value)} />
                        </Field>
                        <Field label="Tamanho maximo MB">
                            <input className="input" type="number" min="1" max="200" value={settings.max_attachment_mb} onChange={(event) => updateField('max_attachment_mb', event.target.value)} />
                        </Field>
                        <Field label="Remetentes bloqueados">
                            <textarea className="input min-h-[90px]" value={settings.blocked_senders || ''} onChange={(event) => updateField('blocked_senders', event.target.value)} placeholder="um email por linha" />
                        </Field>
                    </div>
                </section>
            </div>
        </div>
    )
}

function WhatsAppSettingsPanel() {
    return (
        <div className="space-y-4 p-4">
            <ConfigIntro
                title="WhatsApp"
                text="Configure a recepcao via Twilio WhatsApp. Enquanto as credenciais finais nao estiverem disponiveis, os testes reais podem falhar sem bloquear o restante do desenvolvimento."
            />
            <div className="grid gap-4 xl:grid-cols-2">
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Twilio</div>
                    <div className="grid gap-3 md:grid-cols-2">
                        <Field label="Account SID">
                            <input className="input" placeholder="AC..." />
                        </Field>
                        <Field label="Auth Token">
                            <input className="input" type="password" placeholder="secret" />
                        </Field>
                        <Field label="API Key SID">
                            <input className="input" placeholder="SK..." />
                        </Field>
                        <Field label="API Key Secret">
                            <input className="input" type="password" placeholder="secret" />
                        </Field>
                        <Field label="From Number">
                            <input className="input" placeholder="whatsapp:+14155238886" />
                        </Field>
                        <Field label="Numero de teste">
                            <input className="input" placeholder="whatsapp:+55..." />
                        </Field>
                    </div>
                </section>
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Webhook e midias</div>
                    <div className="grid gap-3">
                        <Field label="Webhook URL">
                            <input className="input" defaultValue="http://127.0.0.1:8070/api/v1/whatsapp/webhook" />
                        </Field>
                        <Field label="Validar assinatura Twilio">
                            <select className="input" defaultValue="enabled">
                                <option value="enabled">Sim</option>
                                <option value="disabled">Nao em dev local</option>
                            </select>
                        </Field>
                        <Field label="Tipos de midia aceitos">
                            <input className="input" defaultValue="application/pdf,image/jpeg,image/png,image/tiff,image/webp" />
                        </Field>
                    </div>
                </section>
            </div>
        </div>
    )
}

function IntegrationSettingsPanel({ settings, onChange, onSave }) {
    const updateField = (field, value) => {
        onChange((current) => ({ ...current, [field]: value }))
    }

    return (
        <div className="space-y-4 p-4">
            <ConfigIntro
                title="Integracoes"
                text="Configure o destino dos dados aprovados. Por enquanto o caminho intermediario e exportacao JSON; Superlogica fica preparado para quando houver acesso ao ambiente."
            />
            <div className="flex justify-end">
                <button type="button" onClick={onSave} className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700">
                    <CheckCircle2 size={16} aria-hidden="true" />
                    Salvar integracoes
                </button>
            </div>
            <div className="grid gap-4 xl:grid-cols-2">
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Export JSON</div>
                    <div className="grid gap-3">
                        <Field label="Ativar exportacao aprovada">
                            <select
                                className="input"
                                value={settings.approved_export_enabled ? 'enabled' : 'disabled'}
                                onChange={(event) => updateField('approved_export_enabled', event.target.value === 'enabled')}
                            >
                                <option value="enabled">Ativado</option>
                                <option value="disabled">Desativado</option>
                            </select>
                        </Field>
                        <Field label="Diretorio destino">
                            <input
                                className="input"
                                value={settings.approved_export_dir || ''}
                                onChange={(event) => updateField('approved_export_dir', event.target.value)}
                            />
                        </Field>
                        <Field label="Formato">
                            <select
                                className="input"
                                value={settings.approved_export_format || 'json'}
                                onChange={(event) => updateField('approved_export_format', event.target.value)}
                            >
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
                            <input
                                className="input"
                                value={settings.superlogica_base_url || ''}
                                onChange={(event) => updateField('superlogica_base_url', event.target.value)}
                                placeholder="https://..."
                            />
                        </Field>
                        <Field label="Credencial">
                            <input className="input" type="password" placeholder="Nao persistido por enquanto" disabled />
                        </Field>
                        <Field label="Modo de envio">
                            <select
                                className="input"
                                value={settings.superlogica_mode || 'disabled'}
                                onChange={(event) => updateField('superlogica_mode', event.target.value)}
                            >
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

function ConfigIntro({ title, text }) {
    return (
        <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3">
            <div className="text-sm font-semibold text-sky-950">{title}</div>
            <div className="mt-1 text-sm leading-6 text-sky-800">{text}</div>
        </div>
    )
}

function ActiveTemplateHeader({ schemaForm, layoutForm, activeLayout, onChangeModel }) {
    return (
        <div className="mb-4 rounded-md border border-zinc-200 bg-zinc-50 px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <div className="text-xs font-semibold uppercase text-zinc-500">Modelo ativo</div>
                    <div className="mt-1 text-sm font-semibold text-zinc-950">
                        {schemaForm.model_name || schemaForm.schema_id || 'Modelo sem nome'}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-600">
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">schema: {schemaForm.schema_id || '-'} · {schemaForm.version || '-'}</span>
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">layout: {activeLayout?.layout || layoutForm.layout || '-'}</span>
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">tipo: {schemaForm.document_type || '-'}</span>
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">status: {schemaForm.status || '-'}</span>
                    </div>
                </div>
                <button type="button" onClick={onChangeModel} className="h-9 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium hover:bg-zinc-100">
                    Alterar modelo
                </button>
            </div>
        </div>
    )
}

function SettingsStepActions({ activeTab, onSaveDraft, onNext }) {
    const currentIndex = SETTINGS_TABS.findIndex((tab) => tab.id === activeTab)
    const nextTab = SETTINGS_TABS[currentIndex + 1]
    return (
        <div className="mt-4 flex flex-wrap items-center justify-end gap-2 border-t border-zinc-200 pt-4">
            <button type="button" onClick={onSaveDraft} className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium hover:bg-zinc-100">
                Salvar rascunho
            </button>
            {nextTab ? (
                <button type="button" onClick={onNext} className="primary-button">
                    Salvar e ir para {nextTab.label}
                </button>
            ) : null}
        </div>
    )
}

function HintPanel({ title, items, onUse }) {
    return (
        <aside className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
            <div className="text-sm font-semibold">{title}</div>
            <div className="mt-3 space-y-2">
                {items.map((item) => (
                    <div key={item} className="flex items-start justify-between gap-2 rounded border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-600">
                        <span>{item}</span>
                        {onUse ? (
                            <button type="button" onClick={() => onUse(item)} className="shrink-0 rounded border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100">
                                Usar
                            </button>
                        ) : null}
                    </div>
                ))}
            </div>
        </aside>
    )
}

function ReferenceDocumentPanel({ documents, selectedDocumentId, onSelectDocument, referenceDocument, fields, review, onReviewChange }) {
    return (
        <div className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-[360px_minmax(360px,1fr)_minmax(360px,1fr)]">
                <section className="rounded-md border border-zinc-200">
                    <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">Documento de referencia</div>
                    <div className="max-h-[520px] overflow-auto">
                        {documents.map((document) => (
                            <button
                                key={document.id}
                                type="button"
                                onClick={() => onSelectDocument(document.id)}
                                className={`block w-full border-b border-zinc-100 px-3 py-2 text-left text-sm hover:bg-zinc-50 ${selectedDocumentId === document.id ? 'bg-zinc-100' : ''}`}
                            >
                                <div className="font-medium">{document.original_filename || document.id}</div>
                                <div className="mt-1 text-xs text-zinc-500">{document.document_type || '-'} · {document.channel || '-'}</div>
                            </button>
                        ))}
                    </div>
                </section>
                <DocumentPreview document={referenceDocument} />
                <HighlightedOcrText text={referenceDocument?.full_transcription || ''} fields={fields} examples={[]} />
            </div>
            <section className="rounded-md border border-zinc-200 bg-white p-4">
                <div className="mb-3 text-sm font-semibold">Revisao da qualidade do OCR</div>
                <div className="grid gap-3 lg:grid-cols-[220px_260px_1fr]">
                    <Field label="Texto confere?">
                        <select value={review.quality} onChange={(event) => onReviewChange({ ...review, quality: event.target.value })} className="input">
                            <option value="pending">Nao revisado</option>
                            <option value="matches">Confere com o documento</option>
                            <option value="minor_issues">Tem pequenas divergencias</option>
                            <option value="major_issues">Nao confere</option>
                        </select>
                    </Field>
                    <Field label="Acao recomendada">
                        <select value={review.action} onChange={(event) => onReviewChange({ ...review, action: event.target.value })} className="input">
                            <option value="review_before_examples">Revisar antes de criar exemplos</option>
                            <option value="use_as_reference">Usar como referencia</option>
                            <option value="reprocess_ocr">Reprocessar OCR</option>
                            <option value="replace_document">Trocar documento</option>
                            <option value="manual_transcription">Corrigir transcricao manualmente</option>
                        </select>
                    </Field>
                    <Field label="Observacoes">
                        <textarea
                            value={review.notes}
                            onChange={(event) => onReviewChange({ ...review, notes: event.target.value })}
                            className="input min-h-[86px]"
                            placeholder="Registre linhas faltantes, campos incorretos, leitura manuscrita ruim ou motivo para reprocessar."
                        />
                    </Field>
                </div>
            </section>
        </div>
    )
}

function DocumentPreview({ document }) {
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">Original</div>
            {!document ? (
                <EmptyState icon={FileText} text="Selecione um documento." />
            ) : document.content_type === 'application/pdf' ? (
                <iframe title="Documento de referencia" src={`/api/ocr/documents/${document.id}/file`} className="h-[520px] w-full" />
            ) : document.content_type?.startsWith('image/') ? (
                <div className="max-h-[520px] overflow-auto p-3">
                    <img src={`/api/ocr/documents/${document.id}/file`} alt="Documento de referencia" className="max-w-full rounded border border-zinc-200" />
                </div>
            ) : (
                <EmptyState icon={FileText} text="Formato sem preview disponivel." />
            )}
        </section>
    )
}

function HighlightedOcrText({ text, fields, examples }) {
    const highlights = [
        ...fields.map((field) => field.name).filter(Boolean),
        ...examples.map((example) => example.source).filter(Boolean),
    ]

    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">OCR com destaques</div>
            <div className="max-h-[520px] overflow-auto whitespace-pre-wrap px-3 py-3 font-mono text-xs leading-5 text-zinc-700">
                {text ? renderHighlightedText(text, highlights) : 'Selecione um documento com transcricao OCR.'}
            </div>
        </section>
    )
}

function SchemaFieldsEditor({ fields, onChange, schemaForm }) {
    const updateField = (index, patch) => {
        onChange(fields.map((field, fieldIndex) => (fieldIndex === index ? { ...field, ...patch } : field)))
    }

    return (
        <div className="space-y-4">
            <section className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
                <div>
                    <div>
                        <div className="text-xs font-semibold uppercase text-zinc-500">Schema em edicao</div>
                        <div className="mt-1 text-sm font-semibold text-zinc-900">
                            {schemaForm.schema_id || 'novo_schema'} · {schemaForm.version || 'v1'}
                        </div>
                        <div className="mt-1 text-sm text-zinc-600">
                            Os campos abaixo pertencem ao schema definido na aba Setup. Ao salvar em Publicacao, eles serao gravados nessa versao.
                        </div>
                    </div>
                </div>
            </section>
            <div className="rounded-md border border-zinc-200">
                <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                    <div className="text-sm font-semibold">Campos de saida</div>
                    <button type="button" onClick={() => onChange([...fields, { name: '', type: 'string', required: false, rule: '' }])} className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100">
                        Adicionar
                    </button>
                </div>
                <div className="divide-y divide-zinc-100">
                    {fields.map((field, index) => (
                        <div key={`${field.name}-${index}`} className="grid gap-2 px-3 py-3 lg:grid-cols-[180px_140px_120px_1fr]">
                            <input value={field.name} onChange={(event) => updateField(index, { name: event.target.value })} className="input" placeholder="campo" />
                            <select value={field.type} onChange={(event) => updateField(index, { type: event.target.value })} className="input">
                                <option value="string">string</option>
                                <option value="decimal">decimal</option>
                                <option value="date">date</option>
                                <option value="cnpj">cnpj</option>
                                <option value="cpf">cpf</option>
                                <option value="enum">enum</option>
                            </select>
                            <label className="flex h-9 items-center gap-2 rounded-md border border-zinc-300 px-3 text-sm text-zinc-700">
                                <input type="checkbox" checked={field.required} onChange={(event) => updateField(index, { required: event.target.checked })} />
                                Obrigatorio
                            </label>
                            <input value={field.rule} onChange={(event) => updateField(index, { rule: event.target.value })} className="input" placeholder="regra de extracao/normalizacao" />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

function ExamplesEditor({ examples, onChange, referenceText }) {
    const updateExample = (index, patch) => {
        onChange(examples.map((example, exampleIndex) => (exampleIndex === index ? { ...example, ...patch } : example)))
    }

    return (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
            <section className="rounded-md border border-zinc-200">
                <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                    <div className="text-sm font-semibold">Few-shot anotados</div>
                    <button type="button" onClick={() => onChange([...examples, { field: '', expected: '', source: '' }])} className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100">
                        Adicionar
                    </button>
                </div>
                <div className="divide-y divide-zinc-100">
                    {examples.map((example, index) => (
                        <div key={`${example.field}-${index}`} className="grid gap-2 px-3 py-3 md:grid-cols-3">
                            <input value={example.field} onChange={(event) => updateExample(index, { field: event.target.value })} className="input" placeholder="campo" />
                            <input value={example.expected} onChange={(event) => updateExample(index, { expected: event.target.value })} className="input" placeholder="valor esperado" />
                            <input value={example.source} onChange={(event) => updateExample(index, { source: event.target.value })} className="input" placeholder="trecho fonte" />
                        </div>
                    ))}
                </div>
            </section>
            <section className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
                <div className="text-sm font-semibold">Texto de apoio</div>
                <div className="mt-3 max-h-[260px] overflow-auto whitespace-pre-wrap rounded border border-zinc-200 bg-white p-3 font-mono text-xs text-zinc-600">
                    {referenceText || 'Selecione um documento na aba OCR referencia para copiar trechos fonte.'}
                </div>
            </section>
        </div>
    )
}

function EmailMetadataModal({ data, onClose }) {
    const isEmail = data.channel === 'email'
    const meta = data.metadata_channel || {}
    const emailRows = isEmail
        ? [
              { label: 'Remetente', value: meta.sender },
              { label: 'Para', value: meta.to },
              { label: 'CC', value: meta.cc },
              { label: 'Assunto', value: meta.subject },
              { label: 'Data de envio', value: meta.date },
              { label: 'Message-ID', value: meta.message_id },
              { label: 'Provedor', value: meta.provider },
          ].filter((row) => row.value)
        : []
    const rows = [{ label: 'Código de Processo', value: data.id }, ...emailRows].filter((row) => row.value)

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
            <div
                className="relative mx-4 w-full max-w-lg rounded-lg border border-zinc-200 bg-white shadow-xl"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between border-b border-zinc-200 px-5 py-4">
                    <div className="min-w-0 flex-1 pr-4">
                        <div className="text-sm font-semibold">{isEmail ? 'Metadados do email' : 'Informações do documento'}</div>
                        {data.filename ? <div className="mt-0.5 text-xs text-zinc-500 truncate">{data.filename}</div> : null}
                    </div>
                    <button type="button" onClick={onClose} className="shrink-0 rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700">
                        <X size={16} aria-hidden="true" />
                    </button>
                </div>
                {isEmail && emailRows.length === 0 ? (
                    <div className="divide-y divide-zinc-100 px-5 py-2">
                        <div className="grid grid-cols-[140px_1fr] gap-3 py-2 text-sm">
                            <dt className="font-medium text-zinc-500">Código de Processo</dt>
                            <dd className="min-w-0 break-all text-zinc-800">{data.id}</dd>
                        </div>
                        <div className="py-4 text-sm text-zinc-500">
                            Metadados do email nao disponiveis para este documento. Reimporte-o para capturar as informacoes.
                        </div>
                    </div>
                ) : (
                    <div className="divide-y divide-zinc-100 px-5 py-2">
                        {rows.map(({ label, value }) => (
                            <div key={label} className="grid grid-cols-[140px_1fr] gap-3 py-2 text-sm">
                                <dt className="font-medium text-zinc-500">{label}</dt>
                                <dd className="min-w-0 break-all text-zinc-800">{value}</dd>
                            </div>
                        ))}
                    </div>
                )}
                {meta.attachments?.length > 0 ? (
                    <div className="border-t border-zinc-200 px-5 py-3">
                        <div className="mb-1.5 text-xs font-semibold uppercase text-zinc-500">Anexos</div>
                        <ul className="space-y-1">
                            {meta.attachments.map((name, i) => (
                                <li key={i} className="flex items-center gap-1.5 text-sm text-zinc-700">
                                    <span className="text-zinc-400">·</span>
                                    {name}
                                </li>
                            ))}
                        </ul>
                    </div>
                ) : null}
                {meta.body_text ? (
                    <div className="border-t border-zinc-200 px-5 py-3">
                        <div className="mb-1 text-xs font-semibold uppercase text-zinc-500">Corpo do email</div>
                        <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-zinc-50 p-3 text-xs text-zinc-700">{meta.body_text}</pre>
                    </div>
                ) : null}
                <div className="border-t border-zinc-200 px-5 py-3 text-right">
                    <button type="button" onClick={onClose} className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-100">
                        Fechar
                    </button>
                </div>
            </div>
        </div>
    )
}

function DocumentTable({
    documents,
    selectedDocumentId = '',
    onSelectDocument,
    compact = false,
    selectable = false,
    bulkSelectedIds = null,
    onBulkSelectionChange = null,
}) {
    const [sortKey, setSortKey] = useState(null)
    const [sortDir, setSortDir] = useState('asc')
    const [emailModalDoc, setEmailModalDoc] = useState(null)
    const selectAllRef = useRef(null)

    function handleSort(key) {
        if (sortKey === key) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc')
        } else {
            setSortKey(key)
            setSortDir('asc')
        }
    }

    const sortedDocuments = sortKey ? [...documents].sort((a, b) => {
        let aVal, bVal
        if (sortKey === 'arquivo') {
            aVal = (a.original_filename || a.id || '').toLowerCase()
            bVal = (b.original_filename || b.id || '').toLowerCase()
        } else if (sortKey === 'status') {
            aVal = (a.status || '').toLowerCase()
            bVal = (b.status || '').toLowerCase()
        } else if (sortKey === 'canal') {
            aVal = (a.channel || '').toLowerCase()
            bVal = (b.channel || '').toLowerCase()
        } else if (sortKey === 'tipo') {
            aVal = (a.document_type || '').toLowerCase()
            bVal = (b.document_type || '').toLowerCase()
        } else if (sortKey === 'atualizado') {
            aVal = a.updated_at || a.received_at || ''
            bVal = b.updated_at || b.received_at || ''
        }
        if (aVal < bVal) return sortDir === 'asc' ? -1 : 1
        if (aVal > bVal) return sortDir === 'asc' ? 1 : -1
        return 0
    }) : documents

    const allSelected = selectable && sortedDocuments.length > 0 && sortedDocuments.every(d => bulkSelectedIds?.has(d.id))
    const someSelected = selectable && !allSelected && sortedDocuments.some(d => bulkSelectedIds?.has(d.id))

    useEffect(() => {
        if (selectAllRef.current) {
            selectAllRef.current.indeterminate = someSelected
        }
    }, [someSelected])

    function toggleAll(e) {
        e.stopPropagation()
        if (!onBulkSelectionChange) return
        const next = new Set(bulkSelectedIds)
        if (allSelected) {
            sortedDocuments.forEach(d => next.delete(d.id))
        } else {
            sortedDocuments.forEach(d => next.add(d.id))
        }
        onBulkSelectionChange(next)
    }

    function toggleOne(e, id) {
        e.stopPropagation()
        if (!onBulkSelectionChange) return
        const next = new Set(bulkSelectedIds)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        onBulkSelectionChange(next)
    }

    const indicator = (col) =>
        sortKey !== col
            ? <span className="ml-1 opacity-30">↕</span>
            : <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>

    const thClass = 'cursor-pointer select-none px-3 py-2 hover:text-zinc-700'

    if (documents.length === 0) {
        return <EmptyState icon={FileText} text="Nenhum documento encontrado." />
    }

    return (
        <>
            <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] border-collapse text-sm">
                    <thead>
                        <tr className="border-b border-zinc-200 bg-zinc-50 text-left text-xs font-semibold uppercase text-zinc-500">
                            {selectable ? (
                                <th className="w-8 px-3 py-2" onClick={(e) => e.stopPropagation()}>
                                    <input
                                        ref={selectAllRef}
                                        type="checkbox"
                                        checked={allSelected}
                                        onChange={toggleAll}
                                        className="h-4 w-4 cursor-pointer rounded border-zinc-300 accent-zinc-700"
                                        title="Selecionar todos"
                                    />
                                </th>
                            ) : null}
                            <th className={thClass} onClick={() => handleSort('arquivo')}>Arquivo{indicator('arquivo')}</th>
                            <th className={thClass} onClick={() => handleSort('status')}>Status{indicator('status')}</th>
                            {compact ? null : <th className={thClass} onClick={() => handleSort('canal')}>Canal{indicator('canal')}</th>}
                            {compact ? null : <th className={thClass} onClick={() => handleSort('tipo')}>Tipo{indicator('tipo')}</th>}
                            <th className={thClass} onClick={() => handleSort('atualizado')}>Atualizado{indicator('atualizado')}</th>
                            <th className="w-8 px-2 py-2"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedDocuments.map((document) => {
                            const isChecked = bulkSelectedIds?.has(document.id) ?? false
                            return (
                                <tr
                                    key={document.id}
                                    onClick={() => onSelectDocument(document.id)}
                                    className={`cursor-pointer border-b border-zinc-100 hover:bg-zinc-50 ${
                                        isChecked ? 'bg-zinc-50' : selectedDocumentId === document.id ? 'bg-zinc-100' : ''
                                    }`}
                                >
                                    {selectable ? (
                                        <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                                            <input
                                                type="checkbox"
                                                checked={isChecked}
                                                onChange={(e) => toggleOne(e, document.id)}
                                                className="h-4 w-4 cursor-pointer rounded border-zinc-300 accent-zinc-700"
                                            />
                                        </td>
                                    ) : null}
                                    <td className="px-3 py-2 font-medium">{document.original_filename || document.id}</td>
                                    <td className="px-3 py-2"><StatusBadge status={document.status} /></td>
                                    {compact ? null : <td className="px-3 py-2">{document.channel || '-'}</td>}
                                    {compact ? null : <td className="px-3 py-2">{document.document_type || '-'}</td>}
                                    <td className="px-3 py-2 text-zinc-500">{formatDate(document.updated_at || document.received_at)}</td>
                                    <td className="px-2 py-2" onClick={(e) => e.stopPropagation()}>
                                        <button
                                            type="button"
                                            title="Ver informações do documento"
                                            onClick={() => setEmailModalDoc({ id: document.id, filename: document.original_filename || document.id, channel: document.channel, metadata_channel: document.metadata_channel })}
                                            className="flex h-6 w-6 items-center justify-center rounded text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
                                        >
                                            <Eye size={14} aria-hidden="true" />
                                        </button>
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
            {emailModalDoc ? <EmailMetadataModal data={emailModalDoc} onClose={() => setEmailModalDoc(null)} /> : null}
        </>
    )
}

function Metric({ label, value }) {
    return (
        <div className="rounded-md border border-zinc-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase text-zinc-500">{label}</div>
            <div className="mt-2 text-2xl font-semibold">{value}</div>
        </div>
    )
}

function ConfigList({ title, items, primaryKey, secondaryKey }) {
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">{title}</div>
            {items.length === 0 ? (
                <EmptyState icon={Settings} text="Nenhuma configuracao cadastrada." />
            ) : (
                <div className="divide-y divide-zinc-100">
                    {items.map((item) => (
                        <div key={item.id} className="px-4 py-3">
                            <div className="text-sm font-medium">{item[primaryKey]}</div>
                            <div className="mt-1 text-xs text-zinc-500">{item[secondaryKey]}</div>
                        </div>
                    ))}
                </div>
            )}
        </section>
    )
}

function Field({ label, children }) {
    return (
        <label className="block">
            <span className="mb-1 block text-xs font-semibold uppercase text-zinc-500">{label}</span>
            {children}
        </label>
    )
}

function Alert({ children, tone = 'neutral' }) {
    const classes = tone === 'error'
        ? 'border-red-200 bg-red-50 text-red-700'
        : 'border-zinc-200 bg-white text-zinc-600'
    return <div className={`mb-4 rounded-md border px-3 py-2 text-sm ${classes}`}>{children}</div>
}

function EmptyState({ icon: Icon, text }) {
    return (
        <div className="flex min-h-[160px] flex-col items-center justify-center gap-2 px-4 py-8 text-center text-sm text-zinc-500">
            <Icon size={24} aria-hidden="true" />
            <span>{text}</span>
        </div>
    )
}

function SearchInput({ value, onChange, placeholder = 'Buscar...' }) {
    return (
        <input
            type="search"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="h-8 w-56 rounded-md border border-zinc-300 bg-white px-3 text-sm placeholder-zinc-400 outline-none focus:border-zinc-500"
        />
    )
}

function StatusBadge({ status }) {
    const isGood = status === 'APPROVED' || status === 'ERP_SENT'
    const isBad = status === 'REJECTED' || status === 'ERP_FAILED' || status === 'OCR_FAILED'
    const classes = isGood
        ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
        : isBad
            ? 'bg-red-50 text-red-700 ring-red-200'
            : 'bg-amber-50 text-amber-700 ring-amber-200'
    return <span className={`inline-flex rounded px-2 py-1 text-xs font-medium ring-1 ${classes}`}>{STATUS_LABELS[status] || status || '-'}</span>
}

function KeyValueGrid({ values }) {
    return (
        <dl className="grid gap-2 sm:grid-cols-3">
            {Object.entries(values).map(([key, value]) => (
                <div key={key} className="rounded-md bg-zinc-50 px-3 py-2">
                    <dt className="text-xs uppercase text-zinc-500">{key}</dt>
                    <dd className="mt-1 text-sm font-medium">{String(value)}</dd>
                </div>
            ))}
        </dl>
    )
}

function buildMetrics(documents) {
    return documents.reduce(
        (acc, document) => {
            acc.total += 1
            if (document.status === 'VALIDATION_PENDING') acc.pending += 1
            if (document.status === 'APPROVED' || document.status === 'ERP_INTEGRATION_REQUESTED' || document.status === 'ERP_SENT') acc.approved += 1
            if (String(document.status || '').includes('FAILED')) acc.failed += 1
            return acc
        },
        { total: 0, pending: 0, approved: 0, failed: 0 },
    )
}

function viewTitle(view) {
    return NAV_ITEMS.find((item) => item.id === view)?.label ?? 'DocuParse'
}

function formatDate(value) {
    if (!value) {
        return '-'
    }
    return new Intl.DateTimeFormat('pt-BR', {
        dateStyle: 'short',
        timeStyle: 'short',
    }).format(new Date(value))
}

function formatEditableValue(value) {
    if (value === null || value === undefined) {
        return ''
    }
    if (typeof value === 'object') {
        return JSON.stringify(value)
    }
    return String(value)
}

function buildLangExtractDefinition({ schemaForm, fields, prompt, examples, normalizationRules, referenceReview, referenceDocument }) {
    let parsedRules = {}
    try {
        parsedRules = JSON.parse(normalizationRules || '{}')
    } catch {
        parsedRules = { parse_error: 'Regras JSON invalidas no momento da geracao.' }
    }

    return {
        kind: 'langextract_template',
        model_name: schemaForm.model_name,
        document_type: schemaForm.document_type,
        status: schemaForm.status,
        fields: fields.filter((field) => field.name.trim()).map((field) => ({
            name: field.name.trim(),
            type: field.type,
            required: Boolean(field.required),
            rule: field.rule,
        })),
        prompt: {
            instructions: prompt,
            guardrails: PROMPT_HINTS,
        },
        examples: examples.filter((example) => example.field.trim() || example.expected.trim() || example.source.trim()),
        reference_review: {
            document_id: referenceDocument?.id || '',
            filename: referenceDocument?.original_filename || '',
            ocr_quality: referenceReview.quality,
            recommended_action: referenceReview.action,
            notes: referenceReview.notes,
        },
        post_processing: parsedRules,
        traceability: {
            require_source_span: true,
            allow_visual_validation: true,
        },
    }
}

function buildLangExtractPreview(text, fields) {
    const output = {}
    fields.forEach((field) => {
        if (!field.name) {
            return
        }
        const source = findLikelySourceLine(text, field.name)
        output[field.name] = {
            value: null,
            source,
            confidence: source ? 0.5 : 0,
            status: source ? 'candidate' : 'missing',
        }
    })
    return JSON.stringify(output, null, 2)
}

function findLikelySourceLine(text, fieldName) {
    if (!text || !fieldName) {
        return ''
    }
    const normalizedField = normalizeSearchText(fieldName).replaceAll('_', ' ')
    return text.split(/\r?\n/).find((line) => normalizeSearchText(line).includes(normalizedField)) || ''
}

function renderHighlightedText(text, highlights) {
    const terms = [...new Set(highlights.map((term) => term.trim()).filter((term) => term.length > 2))]
    if (terms.length === 0) {
        return text
    }

    const pattern = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'gi')
    return text.split(pattern).map((part, index) => {
        const isHighlighted = terms.some((term) => normalizeSearchText(term) === normalizeSearchText(part))
        return isHighlighted ? (
            <mark key={`${part}-${index}`} className="rounded bg-amber-100 px-0.5 text-amber-950">{part}</mark>
        ) : (
            <React.Fragment key={`${part}-${index}`}>{part}</React.Fragment>
        )
    })
}

function normalizeSearchText(value) {
    return String(value || '').trim().toLowerCase()
}

function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function readError(error, fallback) {
    const backendMessage = error?.response?.data?.detail || error?.response?.data?.error
    if (backendMessage) {
        return backendMessage
    }
    if (error?.response?.status === 401) {
        return 'A API recusou a chamada por falta de token interno. Configure VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN no frontend ou remova DOCUPARSE_INTERNAL_SERVICE_TOKEN no backend local.'
    }
    if (error?.code === 'ERR_NETWORK' || error?.message === 'Network Error') {
        return `${fallback} Verifique se backend-core e backend-com estao rodando.`
    }
    return fallback
}

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
