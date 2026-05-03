import React, { useEffect, useMemo, useState } from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import {
    CheckCircle2,
    ClipboardCheck,
    FileText,
    Inbox,
    LayoutDashboard,
    RefreshCw,
    Settings,
    Trash2,
    Upload,
    XCircle,
} from 'lucide-react'
import './index.css'

const internalServiceToken = import.meta.env.VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN
const authHeaders = internalServiceToken ? { Authorization: `Bearer ${internalServiceToken}` } : {}
const api = axios.create({ baseURL: '/api/ocr', headers: authHeaders })
const comApi = axios.create({ baseURL: '/com/api/v1', headers: authHeaders })

const NAV_ITEMS = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'inbox', label: 'Inbox', icon: Inbox },
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'validation', label: 'Validacao', icon: ClipboardCheck },
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
            const [documentsResponse, schemasResponse, layoutsResponse] = await Promise.all([
                api.get('/documents'),
                api.get('/schema-configs'),
                api.get('/layout-configs'),
            ])
            setDocuments(documentsResponse.data ?? [])
            setSchemas(schemasResponse.data ?? [])
            setLayouts(layoutsResponse.data ?? [])
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
    return (
        <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Metric label="Total" value={metrics.total} />
                <Metric label="Pendentes" value={metrics.pending} />
                <Metric label="Aprovados" value={metrics.approved} />
                <Metric label="Falhas" value={metrics.failed} />
            </div>
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">Ultimos documentos</div>
                <DocumentTable documents={documents.slice(0, 8)} onSelectDocument={() => {}} />
            </section>
        </div>
    )
}

function InboxView({ documents, selectedDocumentId, onSelectDocument }) {
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">Documentos recebidos</div>
            <DocumentTable documents={documents} selectedDocumentId={selectedDocumentId} onSelectDocument={onSelectDocument} />
        </section>
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
    const [fieldRows, setFieldRows] = useState([])
    const [submitting, setSubmitting] = useState(false)
    const [actionMessage, setActionMessage] = useState('')
    const [reprocessing, setReprocessing] = useState(false)
    const [deleting, setDeleting] = useState(false)

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

    return (
        <div className="grid gap-4 xl:grid-cols-[340px_minmax(360px,0.9fr)_minmax(460px,1.1fr)]">
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">Fila de validacao</div>
                <DocumentTable documents={documents} selectedDocumentId={selectedDocumentId} onSelectDocument={onSelectDocument} compact />
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

const DEFAULT_LANGEXTRACT_FIELDS = [
    { name: 'fornecedor_nome', type: 'string', required: true, rule: 'Extrair exatamente como aparece no documento.' },
    { name: 'fornecedor_cnpj', type: 'cnpj', required: false, rule: 'Normalizar para 00.000.000/0000-00 quando existir.' },
    { name: 'valor_total', type: 'decimal', required: true, rule: 'Usar o valor total final e converter virgula decimal.' },
    { name: 'vencimento', type: 'date', required: false, rule: 'Normalizar para YYYY-MM-DD.' },
]

const DEFAULT_LANGEXTRACT_PROMPT = [
    'Extraia os campos financeiros do documento.',
    '',
    'Regras:',
    '- Use somente informacoes presentes no texto.',
    '- Nao invente valores ausentes.',
    '- Preserve o trecho fonte usado para cada campo.',
    '- Quando houver multiplos valores, escolha o valor total final.',
    '- Se o campo nao existir, retorne null.',
].join('\n')

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
    const [message, setMessage] = useState('')

    const activeLayout = layouts.find((layout) => (
        layout.schema_config_id === selectedSchemaId
        || (layout.layout === layoutForm.layout && layout.document_type === layoutForm.document_type)
    ))

    useEffect(() => {
        if (!selectedDocumentId) {
            setReferenceDocument(null)
            return
        }
        let ignore = false
        api.get(`/documents/${selectedDocumentId}`)
            .then((response) => {
                if (!ignore) {
                    setReferenceDocument(response.data)
                    setTestOutput(buildLangExtractPreview(response.data.full_transcription || '', fields))
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

    const schemaDefinition = useMemo(() => buildLangExtractDefinition({
        schemaForm,
        fields,
        prompt,
        examples,
        normalizationRules,
        referenceReview,
        referenceDocument,
    }), [schemaForm, fields, prompt, examples, normalizationRules, referenceReview, referenceDocument])

    const loadExistingSchema = (schemaId) => {
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
                                        <select value={selectedSchemaId} onChange={(event) => loadExistingSchema(event.target.value)} className="input">
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
                {activeSettingsArea === 'ocr-routing' ? <OcrSettingsPanel /> : null}
                {activeSettingsArea === 'email' ? <EmailSettingsPanel /> : null}
                {activeSettingsArea === 'whatsapp' ? <WhatsAppSettingsPanel /> : null}
                {activeSettingsArea === 'integrations' ? <IntegrationSettingsPanel /> : null}
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

function OcrSettingsPanel() {
    const activeOcrRoutes = [
        {
            type: 'PDF textual',
            classification: 'digital_pdf',
            engine: 'Docling',
            detail: 'Usado quando o classificador encontra blocos de texto suficientes no PDF.',
        },
        {
            type: 'Imagem/PDF escaneado',
            classification: 'scanned_image',
            engine: 'OpenRouter',
            detail: 'Usado para documentos sem camada textual confiavel, incluindo fotos e PDFs imagem.',
        },
        {
            type: 'Manuscrito complexo',
            classification: 'handwritten_complex',
            engine: 'OpenRouter',
            detail: 'Usado para documentos com escrita manual ou baixa estrutura textual.',
        },
        {
            type: 'Fallback tecnico',
            classification: 'fallback',
            engine: 'Tesseract',
            detail: 'Usado apenas quando o engine primario falha antes de retornar transcricao.',
        },
    ]

    return (
        <div className="space-y-4 p-4">
            <ConfigIntro
                title="OCR"
                text="Perfil operacional atual do OCR. A tela mostra somente os engines usados de fato no fluxo automatico: Docling para PDF textual, OpenRouter para imagem/PDF escaneado e Tesseract como fallback tecnico."
            />
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
                        <Field label="Modelo">
                            <input className="input" defaultValue="OPENROUTER_MODEL do .env" readOnly />
                        </Field>
                        <Field label="Timeout segundos">
                            <input className="input" defaultValue="120" readOnly />
                        </Field>
                        <Field label="Fallback se texto vazio">
                            <input className="input" defaultValue="Reconstruir por key_values do OpenRouter" readOnly />
                        </Field>
                        <Field label="Fallback PDF textual">
                            <input className="input" defaultValue="PyMuPDF dentro do Docling engine" readOnly />
                        </Field>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-zinc-500">
                        PaddleOCR, EasyOCR, TrOCR, LlamaParse e DeepSeek permanecem como codigo legado/opcional, mas nao fazem parte do setup operacional atual.
                    </p>
                </section>
            </div>
        </div>
    )
}

function EmailSettingsPanel() {
    return (
        <div className="space-y-4 p-4">
            <ConfigIntro
                title="Email"
                text="Configure como documentos chegam por email. O endpoint simulado ja aceita anexos; IMAP/webhook real precisa de modelos/API antes de substituir variaveis de ambiente."
            />
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Conta de captura</div>
                    <div className="grid gap-3 md:grid-cols-2">
                        <Field label="Provider">
                            <select className="input" defaultValue="imap">
                                <option value="imap">IMAP</option>
                                <option value="webhook">Webhook</option>
                                <option value="manual_test">Teste manual</option>
                            </select>
                        </Field>
                        <Field label="Pasta monitorada">
                            <input className="input" defaultValue="INBOX" />
                        </Field>
                        <Field label="Host IMAP">
                            <input className="input" placeholder="imap.exemplo.com" />
                        </Field>
                        <Field label="Porta">
                            <input className="input" defaultValue="993" />
                        </Field>
                        <Field label="Usuario">
                            <input className="input" placeholder="documentos@empresa.com" />
                        </Field>
                        <Field label="Senha/app password">
                            <input className="input" type="password" placeholder="armazenar em secret manager" />
                        </Field>
                    </div>
                </section>
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Regras de anexos</div>
                    <div className="space-y-3">
                        <Field label="Tipos aceitos">
                            <input className="input" defaultValue="application/pdf,image/jpeg,image/png,image/tiff,image/webp" />
                        </Field>
                        <Field label="Tamanho maximo MB">
                            <input className="input" defaultValue="20" />
                        </Field>
                        <Field label="Remetentes bloqueados">
                            <textarea className="input min-h-[90px]" placeholder="um email por linha" />
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

function IntegrationSettingsPanel() {
    return (
        <div className="space-y-4 p-4">
            <ConfigIntro
                title="Integracoes"
                text="Configure o destino dos dados aprovados. Por enquanto o caminho intermediario e exportacao JSON; Superlogica fica preparado para quando houver acesso ao ambiente."
            />
            <div className="grid gap-4 xl:grid-cols-2">
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Export JSON</div>
                    <div className="grid gap-3">
                        <Field label="Ativar exportacao aprovada">
                            <select className="input" defaultValue="enabled">
                                <option value="enabled">Ativado</option>
                                <option value="disabled">Desativado</option>
                            </select>
                        </Field>
                        <Field label="Diretorio destino">
                            <input className="input" defaultValue="docuparse-project/exports/approved" />
                        </Field>
                        <Field label="Formato">
                            <select className="input" defaultValue="json">
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
                            <input className="input" placeholder="https://..." />
                        </Field>
                        <Field label="Credencial">
                            <input className="input" type="password" placeholder="pendente" />
                        </Field>
                        <Field label="Modo de envio">
                            <select className="input" defaultValue="disabled">
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

function DocumentTable({ documents, selectedDocumentId = '', onSelectDocument, compact = false }) {
    if (documents.length === 0) {
        return <EmptyState icon={FileText} text="Nenhum documento encontrado." />
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse text-sm">
                <thead>
                    <tr className="border-b border-zinc-200 bg-zinc-50 text-left text-xs font-semibold uppercase text-zinc-500">
                        <th className="px-3 py-2">Arquivo</th>
                        <th className="px-3 py-2">Status</th>
                        {compact ? null : <th className="px-3 py-2">Canal</th>}
                        {compact ? null : <th className="px-3 py-2">Tipo</th>}
                        <th className="px-3 py-2">Atualizado</th>
                    </tr>
                </thead>
                <tbody>
                    {documents.map((document) => (
                        <tr
                            key={document.id}
                            onClick={() => onSelectDocument(document.id)}
                            className={`cursor-pointer border-b border-zinc-100 hover:bg-zinc-50 ${
                                selectedDocumentId === document.id ? 'bg-zinc-100' : ''
                            }`}
                        >
                            <td className="px-3 py-2 font-medium">{document.original_filename || document.id}</td>
                            <td className="px-3 py-2"><StatusBadge status={document.status} /></td>
                            {compact ? null : <td className="px-3 py-2">{document.channel || '-'}</td>}
                            {compact ? null : <td className="px-3 py-2">{document.document_type || '-'}</td>}
                            <td className="px-3 py-2 text-zinc-500">{formatDate(document.updated_at || document.received_at)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
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
