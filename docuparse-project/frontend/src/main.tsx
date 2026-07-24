import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router'
import {
    AlertTriangle,
    Building2,
    Check,
    CheckCircle2,
    ChevronDown,
    ClipboardCheck,
    Copy,
    FileText,
    Inbox,
    LayoutDashboard,
    RefreshCw,
    Settings,
    Trash2,
    Upload,
    Users,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import './index.css'
import { Alert, EmptyState, Field, Metric, SearchInput, KeyValueGrid, DocumentBlobPreview } from './shared/components'
import { asApiError, readError, formatDate } from './shared/utils'
import { api, comApi, adminApi } from './shared/lib/http'
import { useAuth, PermissionGuard } from './modules/auth'
import { RejectedDocumentModal, useDocumentMutations } from './modules/documents'
import type {
    Tenant,
    Document,
    ActiveView,
    SchemaConfig,
    LayoutConfig,
    SchemaField,
    SchemaExample,
    Paginated,
    DocumentListParams,
} from './types'
import { BOLETO_DEFAULT_SCHEMA_ID, BOLETO_DEFAULT_MODEL_NAME, BOLETO_DEFAULT_FIELDS } from './models/boleto/schemas'
import { boletoPromptForDocumentType } from './models/boleto/prompts'
import { BOLETO_DEFAULT_EXAMPLES } from './models/boleto/examples'
import { BOLETO_DEFAULT_RULES } from './models/boleto/rules'
import {
    NOTA_FISCAL_DEFAULT_SCHEMA_ID,
    NOTA_FISCAL_DEFAULT_MODEL_NAME,
    NOTA_FISCAL_DEFAULT_FIELDS,
} from './models/nota_fiscal/schemas'
import { notaFiscalPromptForDocumentType } from './models/nota_fiscal/prompts'
import { NOTA_FISCAL_DEFAULT_EXAMPLES } from './models/nota_fiscal/examples'
import { NOTA_FISCAL_DEFAULT_RULES } from './models/nota_fiscal/rules'
import {
    CONTA_AGUA_DEFAULT_SCHEMA_ID,
    CONTA_AGUA_DEFAULT_MODEL_NAME,
    CONTA_AGUA_DEFAULT_FIELDS,
} from './models/contadeagua/schemas'
import { contaAguaPromptForDocumentType } from './models/contadeagua/prompts'
import { CONTA_AGUA_DEFAULT_EXAMPLES } from './models/contadeagua/examples'
import { CONTA_AGUA_DEFAULT_RULES } from './models/contadeagua/rules'
import { DEFAULT_SCHEMA_ID, DEFAULT_MODEL_NAME, DEFAULT_LANGEXTRACT_FIELDS } from './models/recibo/schemas'
import { DEFAULT_LANGEXTRACT_PROMPT } from './models/recibo/prompts'

export interface NavItem {
    id: ActiveView
    label: string
    icon: LucideIcon
    permission: string
}

export const NAV_ITEMS: NavItem[] = [
    { id: 'upload', label: 'Upload', icon: Upload, permission: 'documents.send' },
    { id: 'inbox', label: 'Inbox', icon: Inbox, permission: 'inbox.view' },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, permission: 'inbox.view' },
    { id: 'validation', label: 'Validacao', icon: ClipboardCheck, permission: 'documents.validate' },
    { id: 'operations', label: 'Operacoes', icon: AlertTriangle, permission: 'operations.access' },
    { id: 'settings', label: 'Configuracoes', icon: Settings, permission: 'roles.manage' },
    { id: 'users', label: 'Usuários', icon: Settings, permission: 'users.manage' },
    { id: 'roles', label: 'Roles', icon: Settings, permission: 'roles.manage' },
    { id: 'tenants', label: 'Tenants', icon: Building2, permission: 'tenants.manage' },
]

// ─── Paginação (feature 009) ──────────────────────────────────────────────────

const PAGE_SIZE = 25

const EMPTY_PAGE: Paginated<Document> = { results: [], count: 0, page: 1, page_size: PAGE_SIZE, total_pages: 0 }

/**
 * Estado de uma listagem paginada server-side de documentos (feature 009).
 * Cada tela mantém sua própria `page`/`search`; alterar a busca reinicia em 1.
 * `refreshSignal` força refetch (ações externas: upload, reprocessar, excluir).
 * `autoRefresh` reconsulta a página atual enquanto houver documentos em
 * processamento, preservando filtros (FR-009).
 *
 * Mantido aqui (não migrado para TanStack Query) só porque `ReferenceDocumentPanel`
 * (Configurações, ainda não extraída — Fase 4f/T036-040) continua o consumindo;
 * todas as telas do módulo `documents` (Fase 4d) já usam `useDocumentsQuery`.
 */
function useDocumentPage(statusCsv?: string, options: { autoRefresh?: boolean; refreshSignal?: number } = {}) {
    const { autoRefresh = false, refreshSignal = 0 } = options
    const [page, setPage] = useState(1)
    const [search, setSearchState] = useState('')
    const [data, setData] = useState<Paginated<Document>>(EMPTY_PAGE)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const fetchPage = useCallback(
        async (silent = false) => {
            if (!silent) setLoading(true)
            setError('')
            try {
                const params: DocumentListParams = { page, page_size: PAGE_SIZE }
                if (statusCsv) params.status = statusCsv
                const term = search.trim()
                if (term) params.search = term
                const response = await api.get<Paginated<Document>>('/documents', { params })
                setData(response.data)
            } catch (requestError) {
                setError(readError(requestError, 'Nao foi possivel carregar os documentos.'))
            } finally {
                if (!silent) setLoading(false)
            }
        },
        [page, search, statusCsv],
    )

    useEffect(() => {
        fetchPage()
    }, [fetchPage, refreshSignal])

    useEffect(() => {
        if (!autoRefresh) return
        const processing = data.results.some((d) => d.status === 'RECEIVED' || d.status === 'OCR_COMPLETED')
        if (!processing) return
        const timer = setTimeout(() => fetchPage(true), 4000)
        return () => clearTimeout(timer)
    }, [data, fetchPage, autoRefresh])

    const setSearch = (value: string) => {
        setSearchState(value)
        setPage(1)
    }

    return { page, setPage, search, setSearch, data, loading, error, refresh: fetchPage }
}

// ─── TenantsView ─────────────────────────────────────────────────────────────

interface TenantUser {
    id: number
    name: string
    email: string
    is_active: boolean
    role: { id: string; name: string } | null
}

function CopySlugButton({ slug }: { slug: string }) {
    const [copied, setCopied] = useState(false)
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(slug)
        } catch {
            const ta = document.createElement('textarea')
            ta.value = slug
            document.body.appendChild(ta)
            ta.select()
            document.execCommand('copy')
            document.body.removeChild(ta)
        }
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
    }
    return (
        <button
            type="button"
            onClick={handleCopy}
            title="Copiar slug"
            className="ml-1.5 inline-flex items-center text-zinc-400 hover:text-zinc-700 transition-colors"
        >
            {copied ? <Check size={12} className="text-green-600" /> : <Copy size={12} />}
        </button>
    )
}

function TenantUsersPanel({ slug, currentTenant }: { slug: string; currentTenant: string | null }) {
    const [users, setUsers] = useState<TenantUser[]>([])
    const [roles, setRoles] = useState<AdminRole[]>([])
    const [loadingUsers, setLoadingUsers] = useState(true)
    const [form, setForm] = useState({ name: '', email: '', password: '', role_id: '' })
    const [submitting, setSubmitting] = useState(false)
    const [formError, setFormError] = useState('')

    const fetchUsers = useCallback(async () => {
        setLoadingUsers(true)
        try {
            const [ur, rr] = await Promise.all([
                adminApi.get<{ data: TenantUser[] }>(`/tenants/${slug}/users/`),
                api.get<AdminRole[]>('/roles'),
            ])
            setUsers(ur.data.data)
            setRoles(rr.data)
        } catch {
            /* ignore — panel shows empty */
        } finally {
            setLoadingUsers(false)
        }
    }, [slug])

    useEffect(() => {
        fetchUsers()
    }, [fetchUsers])

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError('')
        setSubmitting(true)
        try {
            await adminApi.post(`/tenants/${slug}/users/`, form)
            setForm({ name: '', email: '', password: '', role_id: '' })
            await fetchUsers()
        } catch (err: unknown) {
            const s = (err as { response?: { status?: number; data?: { error?: { detail?: string } } } })?.response
                ?.status
            const d = (err as { response?: { data?: { error?: { detail?: string } } } })?.response?.data?.error?.detail
            setFormError(s === 409 ? (d ?? `E-mail já em uso.`) : (d ?? 'Erro ao criar usuário.'))
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="border-t border-zinc-100 bg-zinc-50 px-4 py-4 space-y-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-600 uppercase tracking-wide">
                <Users size={12} />
                Usuários do tenant {slug}
                {currentTenant === slug ? (
                    <span className="ml-1 rounded bg-blue-100 px-1.5 py-0.5 text-blue-700 normal-case font-medium">
                        contexto atual
                    </span>
                ) : null}
            </div>

            {loadingUsers ? (
                <p className="text-xs text-zinc-500">Carregando...</p>
            ) : users.length === 0 ? (
                <p className="text-xs text-zinc-400 italic">Nenhum usuário neste tenant.</p>
            ) : (
                <div className="overflow-x-auto rounded border border-zinc-200 bg-white">
                    <table className="w-full text-xs">
                        <thead>
                            <tr className="border-b border-zinc-100 text-zinc-400 text-left">
                                <th className="px-3 py-2">Nome</th>
                                <th className="px-3 py-2">E-mail</th>
                                <th className="px-3 py-2">Role</th>
                                <th className="px-3 py-2">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-50">
                            {users.map((u) => (
                                <tr key={u.id}>
                                    <td className="px-3 py-2 text-zinc-800">{u.name}</td>
                                    <td className="px-3 py-2 font-mono text-zinc-600">{u.email}</td>
                                    <td className="px-3 py-2 text-zinc-500">{u.role?.name ?? '—'}</td>
                                    <td className="px-3 py-2">
                                        <span
                                            className={`rounded-full px-1.5 py-0.5 text-xs font-medium ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-zinc-100 text-zinc-500'}`}
                                        >
                                            {u.is_active ? 'Ativo' : 'Inativo'}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <form onSubmit={handleCreate} className="rounded border border-zinc-200 bg-white p-3 space-y-2">
                <p className="text-xs font-medium text-zinc-600">Convidar usuário</p>
                <div className="flex flex-wrap gap-2">
                    <input
                        type="text"
                        value={form.name}
                        onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                        required
                        placeholder="Nome"
                        className="h-8 flex-1 min-w-28 rounded border border-zinc-300 px-2 text-xs focus:outline-none focus:border-zinc-500"
                    />
                    <input
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
                        required
                        placeholder="E-mail"
                        className="h-8 flex-1 min-w-36 rounded border border-zinc-300 px-2 text-xs focus:outline-none focus:border-zinc-500"
                    />
                    <input
                        type="password"
                        value={form.password}
                        onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
                        required
                        minLength={8}
                        placeholder="Senha (mín. 8)"
                        className="h-8 flex-1 min-w-32 rounded border border-zinc-300 px-2 text-xs focus:outline-none focus:border-zinc-500"
                    />
                    <select
                        value={form.role_id}
                        onChange={(e) => setForm((p) => ({ ...p, role_id: e.target.value }))}
                        required
                        className="h-8 flex-1 min-w-28 rounded border border-zinc-300 px-2 text-xs bg-white focus:outline-none focus:border-zinc-500"
                    >
                        <option value="">Selecionar role</option>
                        {roles.map((r) => (
                            <option key={r.id} value={r.id}>
                                {r.name}
                            </option>
                        ))}
                    </select>
                    <button
                        type="submit"
                        disabled={submitting}
                        className="h-8 rounded bg-zinc-900 px-3 text-xs font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                    >
                        {submitting ? '...' : 'Convidar'}
                    </button>
                </div>
                {formError ? <p className="text-xs text-red-600">{formError}</p> : null}
            </form>
        </div>
    )
}

export function TenantsView() {
    const { currentTenant, switchTenant } = useAuth()
    const [tenants, setTenants] = useState<Tenant[]>([])
    const [loadingList, setLoadingList] = useState(true)
    const [listError, setListError] = useState('')
    const [formSlug, setFormSlug] = useState('')
    const [formName, setFormName] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [formError, setFormError] = useState('')
    const [toggleError, setToggleError] = useState<Record<string, string>>({})
    const [expandedSlug, setExpandedSlug] = useState<string | null>(null)
    const [switchingSlug, setSwitchingSlug] = useState<string | null>(null)
    const [switchError, setSwitchError] = useState<Record<string, string>>({})

    const fetchTenants = useCallback(async () => {
        setLoadingList(true)
        setListError('')
        try {
            const r = await adminApi.get<{ data: Tenant[] }>('/tenants/')
            setTenants(r.data.data)
        } catch {
            setListError('Falha ao carregar tenants.')
        } finally {
            setLoadingList(false)
        }
    }, [])

    useEffect(() => {
        fetchTenants()
    }, [fetchTenants])

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault()
        setSubmitting(true)
        setFormError('')
        try {
            await adminApi.post('/tenants/', { slug: formSlug, name: formName })
            setFormSlug('')
            setFormName('')
            await fetchTenants()
        } catch (err: unknown) {
            const s = (err as { response?: { status?: number; data?: { error?: { detail?: string } } } })?.response
                ?.status
            const detail = (err as { response?: { data?: { error?: { detail?: string } } } })?.response?.data?.error
                ?.detail
            setFormError(
                s === 409
                    ? (detail ?? `Tenant com slug "${formSlug}" já existe.`)
                    : (detail ?? 'Erro ao criar tenant.'),
            )
        } finally {
            setSubmitting(false)
        }
    }

    const handleToggle = async (slug: string, currentActive: boolean) => {
        setToggleError((prev) => ({ ...prev, [slug]: '' }))
        try {
            await adminApi.patch(`/tenants/${slug}/`, { is_active: !currentActive })
            await fetchTenants()
        } catch (err: unknown) {
            const s = (err as { response?: { status?: number; data?: { error?: { detail?: string } } } })?.response
                ?.status
            const detail = (err as { response?: { data?: { error?: { detail?: string } } } })?.response?.data?.error
                ?.detail
            setToggleError((prev) => ({
                ...prev,
                [slug]:
                    s === 409
                        ? (detail ?? 'Não é possível desativar o único tenant ativo.')
                        : (detail ?? 'Erro ao atualizar tenant.'),
            }))
        }
    }

    const handleSwitch = async (slug: string) => {
        setSwitchError((prev) => ({ ...prev, [slug]: '' }))
        setSwitchingSlug(slug)
        try {
            await switchTenant(slug)
        } catch (err: unknown) {
            const detail = (err as { response?: { data?: { error?: { detail?: string } } } })?.response?.data?.error
                ?.detail
            setSwitchError((prev) => ({ ...prev, [slug]: detail ?? 'Erro ao alternar tenant.' }))
        } finally {
            setSwitchingSlug(null)
        }
    }

    return (
        <div className="space-y-6">
            <form onSubmit={handleCreate} className="rounded-lg border border-zinc-200 bg-white p-5">
                <h2 className="mb-4 text-sm font-semibold text-zinc-800">Novo Tenant</h2>
                <div className="flex flex-wrap gap-3">
                    <input
                        type="text"
                        value={formSlug}
                        onChange={(e) => setFormSlug(e.target.value)}
                        required
                        maxLength={50}
                        pattern="[a-z0-9-]+"
                        placeholder="slug (ex: empresa-abc)"
                        title="Apenas letras minúsculas, números e hífens"
                        className="h-9 flex-1 min-w-40 rounded-md border border-zinc-300 px-3 text-sm focus:border-zinc-500 focus:outline-none"
                    />
                    <input
                        type="text"
                        value={formName}
                        onChange={(e) => setFormName(e.target.value)}
                        required
                        placeholder="Nome da empresa"
                        className="h-9 flex-1 min-w-40 rounded-md border border-zinc-300 px-3 text-sm focus:border-zinc-500 focus:outline-none"
                    />
                    <button
                        type="submit"
                        disabled={submitting}
                        className="h-9 rounded-md bg-zinc-900 px-4 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                    >
                        {submitting ? 'Criando...' : 'Criar'}
                    </button>
                </div>
                {formError ? <p className="mt-2 text-xs text-red-600">{formError}</p> : null}
            </form>

            {listError ? <p className="text-sm text-red-600">{listError}</p> : null}
            {loadingList ? <p className="text-sm text-zinc-500">Carregando...</p> : null}

            {!loadingList && tenants.length > 0 ? (
                <div className="rounded-lg border border-zinc-200 bg-white overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-zinc-200 text-left text-xs font-medium text-zinc-500">
                                <th className="px-4 py-3">Slug</th>
                                <th className="px-4 py-3">Nome</th>
                                <th className="px-4 py-3">Status</th>
                                <th className="px-4 py-3">Criado em</th>
                                <th className="px-4 py-3"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {tenants.map((t) => (
                                <React.Fragment key={t.slug}>
                                    <tr
                                        className={`border-b border-zinc-100 hover:bg-zinc-50 ${expandedSlug === t.slug ? 'bg-zinc-50' : ''}`}
                                    >
                                        <td className="px-4 py-3 font-mono text-xs text-zinc-700">
                                            <span className="inline-flex items-center gap-0.5">
                                                {t.slug}
                                                <CopySlugButton slug={t.slug} />
                                                {currentTenant === t.slug ? (
                                                    <span className="ml-1.5 rounded bg-blue-100 px-1 py-0.5 text-blue-700 text-[10px] font-medium not-mono">
                                                        atual
                                                    </span>
                                                ) : null}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-zinc-800">{t.name}</td>
                                        <td className="px-4 py-3">
                                            <span
                                                className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${t.is_active ? 'bg-green-100 text-green-700' : 'bg-zinc-100 text-zinc-500'}`}
                                            >
                                                {t.is_active ? 'Ativo' : 'Inativo'}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-zinc-500">
                                            {new Date(t.created_at).toLocaleDateString('pt-BR')}
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex flex-wrap items-center justify-end gap-1.5">
                                                <button
                                                    type="button"
                                                    onClick={() => handleSwitch(t.slug)}
                                                    disabled={switchingSlug === t.slug || !t.is_active}
                                                    className="rounded px-2 py-1 text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-40"
                                                >
                                                    {switchingSlug === t.slug ? '...' : 'Alternar'}
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() =>
                                                        setExpandedSlug(expandedSlug === t.slug ? null : t.slug)
                                                    }
                                                    className="inline-flex items-center gap-0.5 rounded px-2 py-1 text-xs font-medium bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
                                                >
                                                    <Users size={11} />
                                                    Usuários
                                                    <ChevronDown
                                                        size={11}
                                                        className={`transition-transform ${expandedSlug === t.slug ? 'rotate-180' : ''}`}
                                                    />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => handleToggle(t.slug, t.is_active)}
                                                    className={`rounded px-2 py-1 text-xs font-medium ${t.is_active ? 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200' : 'bg-green-50 text-green-700 hover:bg-green-100'}`}
                                                >
                                                    {t.is_active ? 'Desativar' : 'Ativar'}
                                                </button>
                                                {toggleError[t.slug] || switchError[t.slug] ? (
                                                    <span className="w-full text-right text-xs text-red-600">
                                                        {toggleError[t.slug] || switchError[t.slug]}
                                                    </span>
                                                ) : null}
                                            </div>
                                        </td>
                                    </tr>
                                    {expandedSlug === t.slug ? (
                                        <tr>
                                            <td colSpan={5} className="p-0">
                                                <TenantUsersPanel slug={t.slug} currentTenant={currentTenant} />
                                            </td>
                                        </tr>
                                    ) : null}
                                </React.Fragment>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : null}
        </div>
    )
}

// ─── AppLayout ───────────────────────────────────────────────────────────────

/** Caminho de rota (React Router) para um item de NAV_ITEMS — mapeamento 1:1, `id` vira `/id`. */
export function navPath(id: ActiveView): string {
    return `/${id}`
}

function activeViewForPath(pathname: string): ActiveView | undefined {
    return NAV_ITEMS.find((item) => navPath(item.id) === pathname)?.id
}

/**
 * Estado/handlers de nível de app (schemas/layouts/documento selecionado/ações de
 * documento) hoje mantidos aqui porque as telas que os consomem (Dashboard, Inbox,
 * Validação, etc.) ainda não foram extraídas para `modules/documents` (Fase 4d) —
 * quando forem, isto vira TanStack Query e este contexto desaparece.
 */
export interface AppOutletContext {
    schemas: SchemaConfig[]
    layouts: LayoutConfig[]
    selectedDocumentId: string
    selectedDocument: Document | null
    refreshSignal: number
    refreshData: (silent?: boolean) => Promise<void>
    navigateToValidation: (documentId: string) => void
    handleReprocessDocument: (id: string) => Promise<void>
    handleDeleteDocument: (id: string) => Promise<void>
    onSelectRejected: (doc: Document | null) => void
}

export function AppLayout() {
    const { user, logout, hasPermission, currentTenant } = useAuth()
    const { reprocessDocument, deleteDocument } = useDocumentMutations()
    const location = useLocation()
    const navigate = useNavigate()
    const activeView = activeViewForPath(location.pathname)
    const [schemas, setSchemas] = useState<SchemaConfig[]>([])
    const [layouts, setLayouts] = useState<LayoutConfig[]>([])
    const [selectedDocumentId, setSelectedDocumentId] = useState('')
    const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [rejectedModal, setRejectedModal] = useState<Document | null>(null)
    // Sinal incrementado para forçar as listagens paginadas a recarregar a página
    // atual após ações externas (upload, reprocessar, excluir, "Atualizar").
    const [refreshSignal, setRefreshSignal] = useState(0)

    // feature 009: as listagens (Dashboard/Inbox/Aprovados/Rejeitados) passaram a
    // buscar suas próprias páginas server-side (ver useDocumentPage). Aqui só
    // carregamos schemas/layouts (Validação/Configurações) e o documento
    // selecionado; os documentos não são mais carregados em massa no cliente.
    const refreshData = async (silent = false) => {
        setRefreshSignal((n) => n + 1)
        if (!hasPermission('inbox.view')) return
        if (!silent) setLoading(true)
        setError('')
        try {
            const [schemasResult, layoutsResult] = await Promise.allSettled([
                api.get<SchemaConfig[]>('/schema-configs'),
                api.get<LayoutConfig[]>('/layout-configs'),
            ])

            if (schemasResult.status === 'fulfilled') {
                setSchemas(schemasResult.value.data ?? [])
            }

            if (layoutsResult.status === 'fulfilled') {
                setLayouts(layoutsResult.value.data ?? [])
            }

            const configError = [schemasResult, layoutsResult].find((result) => result.status === 'rejected')
            if (configError) {
                setError(readError(configError.reason, 'Nao foi possivel carregar todas as configuracoes.'))
            }

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
                <aside className="hidden w-64 shrink-0 border-r border-zinc-200 bg-white md:block">
                    <div className="border-b border-zinc-200 px-5 py-5">
                        <div className="text-lg font-semibold">DocuParse</div>
                        <div className="mt-1 text-xs text-zinc-500">{user?.name || 'Operacao de documentos'}</div>
                        {currentTenant ? (
                            <div className="mt-1 inline-flex items-center gap-1 rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-600">
                                <Building2 size={10} aria-hidden="true" />
                                {currentTenant}
                            </div>
                        ) : null}
                    </div>
                    <nav className="space-y-1 px-3 py-4">
                        {NAV_ITEMS.map((item) => (
                            <PermissionGuard key={item.id} code={item.permission}>
                                <NavButton item={item} active={activeView === item.id} />
                            </PermissionGuard>
                        ))}
                    </nav>
                    <div className="border-t border-zinc-200 px-3 py-3">
                        <button
                            type="button"
                            onClick={logout}
                            className="flex w-full h-9 items-center gap-2 rounded-md px-3 text-sm font-medium text-zinc-600 hover:bg-zinc-100"
                        >
                            Sair
                        </button>
                    </div>
                </aside>

                <main className="min-w-0 flex-1">
                    <header className="border-b border-zinc-200 bg-white px-4 py-4 md:px-6">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <h1 className="text-xl font-semibold">{viewTitle(activeView)}</h1>
                                <p className="mt-1 text-sm text-zinc-500">
                                    Fluxo de captura, validacao e exportacao aprovado.
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={refreshData as unknown as React.MouseEventHandler<HTMLButtonElement>}
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
                                <PermissionGuard key={item.id} code={item.permission}>
                                    <NavButton item={item} active={activeView === item.id} compact />
                                </PermissionGuard>
                            ))}
                        </div>
                    </div>

                    <section className="px-4 py-5 md:px-6">
                        {error ? <Alert tone="error">{error}</Alert> : null}
                        {loading ? <Alert>Carregando dados...</Alert> : null}

                        <Outlet
                            context={
                                {
                                    schemas,
                                    layouts,
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

function NavButton({ item, active, compact = false }: { item: NavItem; active: boolean; compact?: boolean }) {
    const Icon = item.icon
    return (
        <Link
            to={navPath(item.id)}
            className={`flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium ${
                compact ? 'shrink-0' : 'w-full'
            } ${active ? 'bg-zinc-900 text-white' : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950'}`}
        >
            <Icon size={17} aria-hidden="true" />
            {item.label}
        </Link>
    )
}

const DEFAULT_DLQ_STREAM = 'ocr.completed.dlq'

// Os eventos/streams de DLQ têm forma dinâmica (payloads de workers diversos);
// campos ad-hoc são renderizados diretamente, por isso o índice permissivo.
interface DlqStream {
    stream: string
    count: number
    latest?: DlqEvent
    [key: string]: unknown
}

interface DlqSummary {
    total: number
    streams: DlqStream[]
}

interface DlqEvent {
    id?: string
    original_stream?: string
    source?: string
    error_type?: string
    error?: string
    payload?: unknown
    occurred_at?: string | number | Date | null
    event_type?: string
    event_id?: string
    [key: string]: unknown
}

export function OperationsView() {
    const [summary, setSummary] = useState<DlqSummary>({ total: 0, streams: [] })
    const [selectedStream, setSelectedStream] = useState(DEFAULT_DLQ_STREAM)
    const [events, setEvents] = useState<DlqEvent[]>([])
    const [selectedEvent, setSelectedEvent] = useState<DlqEvent | null>(null)
    const [loading, setLoading] = useState(false)
    const [requeueing, setRequeueing] = useState(false)
    const [message, setMessage] = useState('')
    const [messageTone, setMessageTone] = useState<'neutral' | 'error'>('neutral')

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

    const selectStream = (stream: string) => {
        setSelectedStream(stream)
        loadOperations(stream)
    }

    const requeueSelectedEvent = async ({ execute }: { execute: boolean }) => {
        if (!selectedEvent || requeueing) {
            return
        }
        if (
            execute &&
            !window.confirm(
                'Reenfileirar este payload original para reprocessamento? O registro da DLQ sera mantido para auditoria.',
            )
        ) {
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
                        <div className="mt-1 text-xs text-zinc-500">
                            Eventos que falharam nos workers e aguardam revisao operacional.
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={() => loadOperations(selectedStream)}
                        className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                    >
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
                            <div className="mt-1 truncate text-xs text-zinc-500">
                                {item.latest?.error_type || 'Sem eventos'}
                            </div>
                        </button>
                    ))}
                </div>
            </section>

            <section className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
                <div className="rounded-md border border-zinc-200 bg-white">
                    <div className="border-b border-zinc-200 px-4 py-3">
                        <div className="text-sm font-semibold">{selectedStream}</div>
                        <div className="mt-1 text-xs text-zinc-500">
                            Selecione um evento para ver erro e payload original.
                        </div>
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
                                        <td className="whitespace-nowrap px-4 py-3 text-zinc-600">
                                            {formatDate(event.occurred_at)}
                                        </td>
                                        <td className="whitespace-nowrap px-4 py-3">{event.source || '-'}</td>
                                        <td className="px-4 py-3">
                                            <div className="font-medium">{event.event_type || '-'}</div>
                                            <div className="max-w-[220px] truncate text-xs text-zinc-500">
                                                {event.event_id || '-'}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="font-medium text-red-700">{event.error_type || '-'}</div>
                                            <div className="max-w-[360px] truncate text-xs text-zinc-500">
                                                {event.error || '-'}
                                            </div>
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
                                <div className="rounded-md border border-red-100 bg-red-50 p-3 text-sm text-red-800">
                                    {selectedEvent.error || '-'}
                                </div>
                            </div>
                            <div>
                                <div className="mb-1 text-xs font-semibold uppercase text-zinc-500">
                                    Payload original
                                </div>
                                <pre className="max-h-[420px] overflow-auto rounded-md bg-zinc-950 p-3 text-xs text-zinc-50">
                                    {JSON.stringify(selectedEvent.payload || {}, null, 2)}
                                </pre>
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

export function UploadView({ onUploaded }: { onUploaded: () => void | Promise<unknown> }) {
    const [file, setFile] = useState<File | null>(null)
    const [previewUrl, setPreviewUrl] = useState('')
    const [sender, setSender] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [message, setMessage] = useState('')

    const canSubmit = Boolean(file) && !submitting

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
        if (file) formData.append('file', file)
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
                        <img
                            src={previewUrl}
                            alt="Preview do arquivo selecionado"
                            className="max-w-full rounded border border-zinc-200"
                        />
                    </div>
                )}
            </section>
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

const SETTINGS_TAB_HELP: Record<string, { title: string; text: string }> = {
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

// Formas dos formulários de configuração (estado local da SettingsView). Espelham
// os payloads dos respectivos endpoints; campos numéricos podem receber strings
// dos inputs antes do envio (comportamento preservado).
interface OcrSettingsForm {
    digital_pdf_engine: string
    scanned_image_engine: string
    handwritten_engine: string
    technical_fallback_engine: string
    openrouter_model: string
    openrouter_fallback_model: string
    timeout_seconds: number | string
    retry_empty_text_enabled: boolean
    digital_pdf_min_text_blocks: number | string
}

interface EmailSettingsForm {
    provider: string
    inbox_folder: string
    imap_host: string
    imap_port: number | string
    username: string
    webhook_url: string
    accepted_content_types: string
    max_attachment_mb: number | string
    blocked_senders: string
    is_active: boolean
}

interface IntegrationSettingsForm {
    approved_export_enabled: boolean
    approved_export_dir: string
    approved_export_format: string
    superlogica_base_url: string
    superlogica_mode: string
}

interface SchemaForm {
    schema_id: string
    version: string
    model_name: string
    document_type: string
    status: string
}

interface LayoutForm {
    layout: string
    document_type: string
    schema_config_id: string
    confidence_threshold: string
}

interface ReferenceReview {
    quality: string
    action: string
    notes: string
}

export function SettingsView({
    schemas,
    layouts,
    onChanged,
}: {
    schemas: SchemaConfig[]
    layouts: LayoutConfig[]
    onChanged: () => void | Promise<unknown>
}) {
    const { currentTenant } = useAuth()
    const [activeSettingsArea, setActiveSettingsArea] = useState('extraction')
    const [activeTab, setActiveTab] = useState('setup')
    const [schemaForm, setSchemaForm] = useState<SchemaForm>({
        schema_id: 'recibo_servico',
        version: 'v1',
        model_name: 'Recibo de servico',
        document_type: 'scanned_image',
        status: 'draft',
    })
    const [layoutForm, setLayoutForm] = useState<LayoutForm>({
        layout: 'recibo',
        document_type: 'scanned_image',
        schema_config_id: '',
        confidence_threshold: '0.75',
    })
    const [fields, setFields] = useState(DEFAULT_LANGEXTRACT_FIELDS)
    const [prompt, setPrompt] = useState(DEFAULT_LANGEXTRACT_PROMPT)
    const [normalizationRules, setNormalizationRules] = useState(
        '{\n  "valor_total": { "type": "decimal", "required": true, "min": 0 },\n  "fornecedor_cnpj": { "type": "cnpj", "validate_checksum": true }\n}',
    )
    const [examples, setExamples] = useState<SchemaExample[]>([
        {
            field: 'valor_total',
            expected: '120.00',
            source: 'Valor: 120,00',
        },
    ])
    const [referenceReview, setReferenceReview] = useState<ReferenceReview>({
        quality: 'pending',
        action: 'review_before_examples',
        notes: '',
    })
    const [selectedDocumentId, setSelectedDocumentId] = useState('')
    const [referenceDocument, setReferenceDocument] = useState<Document | null>(null)
    const [testOutput, setTestOutput] = useState('{}')
    const [selectedSchemaId, setSelectedSchemaId] = useState('')
    // Track whether schema selection came from the user or auto-detection.
    const [schemaSelectionSource, setSchemaSelectionSource] = useState('auto')
    const [message, setMessage] = useState('')
    const [integrationSettings, setIntegrationSettings] = useState<IntegrationSettingsForm>({
        approved_export_enabled: true,
        approved_export_dir: 'docuparse-project/exports/approved',
        approved_export_format: 'json',
        superlogica_base_url: '',
        superlogica_mode: 'disabled',
    })
    const [ocrSettings, setOcrSettings] = useState<OcrSettingsForm>({
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
    const [emailSettings, setEmailSettings] = useState<EmailSettingsForm>({
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

    const activeLayout = layouts.find(
        (layout) =>
            layout.schema_config_id === selectedSchemaId ||
            (layout.layout === layoutForm.layout && layout.document_type === layoutForm.document_type),
    )

    useEffect(() => {
        if (!selectedDocumentId) {
            setReferenceDocument(null)
            return
        }
        // Reset to auto so new documents can trigger default selection.
        setSchemaSelectionSource('auto')
        let ignore = false
        api.get<Document>(`/documents/${selectedDocumentId}`)
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

    // Auto-select model when OCR text is loaded — classification delegated to the backend.
    useEffect(() => {
        const rawText = referenceDocument?.full_transcription || ''
        if (!rawText || schemaSelectionSource === 'manual') return

        const capturedSchemaId = schemaForm.schema_id

        let ignore = false
        api.post<{ schema_id?: string }>('/classify-text', { text: rawText })
            .then((res) => {
                if (ignore) return
                const detectedType = res.data?.schema_id
                const docType = referenceDocument?.document_type || schemaForm.document_type

                if (detectedType === NOTA_FISCAL_DEFAULT_SCHEMA_ID) {
                    const notaPrompt = notaFiscalPromptForDocumentType(docType)
                    if (notaFiscalSchema) {
                        loadExistingSchema(notaFiscalSchema.id, { source: 'auto' })
                        setFields(NOTA_FISCAL_DEFAULT_FIELDS)
                        setExamples(NOTA_FISCAL_DEFAULT_EXAMPLES)
                        setNormalizationRules(JSON.stringify(NOTA_FISCAL_DEFAULT_RULES, null, 2))
                        setSchemaForm((current) => ({
                            ...current,
                            model_name: NOTA_FISCAL_DEFAULT_MODEL_NAME,
                            schema_id: NOTA_FISCAL_DEFAULT_SCHEMA_ID,
                            document_type: docType,
                        }))
                        setPrompt(notaPrompt)
                        return
                    }
                    setSelectedSchemaId('')
                    setSchemaForm((current) => ({
                        ...current,
                        model_name: NOTA_FISCAL_DEFAULT_MODEL_NAME,
                        schema_id: NOTA_FISCAL_DEFAULT_SCHEMA_ID,
                        document_type: docType,
                    }))
                    setFields(NOTA_FISCAL_DEFAULT_FIELDS)
                    setPrompt(notaPrompt)
                    setExamples(NOTA_FISCAL_DEFAULT_EXAMPLES)
                    setNormalizationRules(JSON.stringify(NOTA_FISCAL_DEFAULT_RULES, null, 2))
                    return
                }

                if (detectedType === CONTA_AGUA_DEFAULT_SCHEMA_ID) {
                    const aguaPrompt = contaAguaPromptForDocumentType(docType)
                    if (contaAguaSchema) {
                        loadExistingSchema(contaAguaSchema.id, { source: 'auto' })
                        setFields(CONTA_AGUA_DEFAULT_FIELDS)
                        setExamples(CONTA_AGUA_DEFAULT_EXAMPLES)
                        setNormalizationRules(JSON.stringify(CONTA_AGUA_DEFAULT_RULES, null, 2))
                        setSchemaForm((current) => ({
                            ...current,
                            model_name: CONTA_AGUA_DEFAULT_MODEL_NAME,
                            schema_id: CONTA_AGUA_DEFAULT_SCHEMA_ID,
                            document_type: docType,
                        }))
                        setPrompt(aguaPrompt)
                        return
                    }
                    setSelectedSchemaId('')
                    setSchemaForm((current) => ({
                        ...current,
                        model_name: CONTA_AGUA_DEFAULT_MODEL_NAME,
                        schema_id: CONTA_AGUA_DEFAULT_SCHEMA_ID,
                        document_type: docType,
                    }))
                    setFields(CONTA_AGUA_DEFAULT_FIELDS)
                    setPrompt(aguaPrompt)
                    setExamples(CONTA_AGUA_DEFAULT_EXAMPLES)
                    setNormalizationRules(JSON.stringify(CONTA_AGUA_DEFAULT_RULES, null, 2))
                    return
                }

                if (detectedType === BOLETO_DEFAULT_SCHEMA_ID) {
                    const boletoPrompt = boletoPromptForDocumentType(docType)
                    if (boletoSchema) {
                        loadExistingSchema(boletoSchema.id, { source: 'auto' })
                        setFields(BOLETO_DEFAULT_FIELDS)
                        setExamples(BOLETO_DEFAULT_EXAMPLES)
                        setNormalizationRules(JSON.stringify(BOLETO_DEFAULT_RULES, null, 2))
                        setSchemaForm((current) => ({
                            ...current,
                            model_name: BOLETO_DEFAULT_MODEL_NAME,
                            schema_id: BOLETO_DEFAULT_SCHEMA_ID,
                            document_type: docType,
                        }))
                        setPrompt(boletoPrompt)
                        return
                    }
                    setSelectedSchemaId('')
                    setSchemaForm((current) => ({
                        ...current,
                        model_name: BOLETO_DEFAULT_MODEL_NAME,
                        schema_id: BOLETO_DEFAULT_SCHEMA_ID,
                        document_type: docType,
                    }))
                    setFields(BOLETO_DEFAULT_FIELDS)
                    setPrompt(boletoPrompt)
                    setExamples(BOLETO_DEFAULT_EXAMPLES)
                    setNormalizationRules(JSON.stringify(BOLETO_DEFAULT_RULES, null, 2))
                    return
                }

                // No match — reset to default if currently on a known auto-selected schema.
                if (
                    [BOLETO_DEFAULT_SCHEMA_ID, NOTA_FISCAL_DEFAULT_SCHEMA_ID, CONTA_AGUA_DEFAULT_SCHEMA_ID].includes(
                        capturedSchemaId,
                    )
                ) {
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
            })
            .catch(() => {})
        return () => {
            ignore = true
        }
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
        api.get('/settings/integrations', { params: { tenant: currentTenant ?? '' } })
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
        api.get('/settings/ocr', { params: { tenant: currentTenant ?? '' } })
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
        api.get('/settings/email', { params: { tenant: currentTenant ?? '' } })
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

    const schemaDefinition = useMemo(
        () =>
            buildLangExtractDefinition({
                schemaForm,
                fields,
                prompt,
                examples,
                normalizationRules,
                referenceReview,
                referenceDocument,
            }),
        [schemaForm, fields, prompt, examples, normalizationRules, referenceReview, referenceDocument],
    )

    const loadExistingSchema = (schemaId: string, { source = 'manual' }: { source?: string } = {}) => {
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
            schema_id: schema.schema_id ?? current.schema_id,
            version: schema.version ?? current.version,
            model_name: definition.model_name || schema.schema_id || current.model_name,
            document_type: definition.document_type || current.document_type,
            status: definition.status || current.status,
        }))
        const linkedLayout = layouts.find((layout) => layout.schema_config_id === schema.id)
        if (linkedLayout) {
            setLayoutForm((current) => ({
                ...current,
                layout: linkedLayout.layout ?? current.layout,
                document_type: linkedLayout.document_type ?? current.document_type,
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
            setFields(
                definition.fields.map((field: Partial<SchemaField>) => ({
                    name: field.name || '',
                    type: field.type || 'string',
                    required: Boolean(field.required),
                    rule: field.rule || '',
                })),
            )
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
                tenant_slug: currentTenant ?? '',
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
                tenant_slug: currentTenant ?? '',
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
                tenant_slug: currentTenant ?? '',
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
                params: { tenant_id: currentTenant ?? '' },
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

    const pollWhatsApp = async () => {
        setMessage('')
        try {
            const response = await comApi.post('/whatsapp/poll', null, {
                params: { tenant_id: currentTenant ?? '' },
            })
            const imported = response.data.accepted_count || 0
            const duplicates = response.data.duplicate_count || 0
            let pollMsg = `Captura WhatsApp executada: ${imported} documento(s) importado(s).`
            if (duplicates > 0) {
                pollMsg += ` ${duplicates} já existia(m) no sistema e foi(ram) ignorado(s).`
            }
            setMessage(pollMsg)
            await onChanged()
        } catch (requestError) {
            setMessage(readError(requestError, 'Falha ao executar captura WhatsApp.'))
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
                                <ActiveTemplateHeader
                                    schemaForm={schemaForm}
                                    layoutForm={layoutForm}
                                    activeLayout={activeLayout}
                                    onChangeModel={() => setActiveTab('setup')}
                                />
                            ) : null}
                            {activeTab === 'setup' ? (
                                <div className="space-y-4">
                                    <section className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
                                        <div className="grid gap-3 lg:grid-cols-[minmax(260px,1fr)_220px]">
                                            <Field label="Selecionar modelo existente">
                                                <select
                                                    value={selectedSchemaId}
                                                    onChange={(event) =>
                                                        loadExistingSchema(event.target.value, { source: 'manual' })
                                                    }
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
                                                        schema_id: 'novo_modelo',
                                                        version: 'v1',
                                                        model_name: 'Novo modelo',
                                                        document_type: 'scanned_image',
                                                        status: 'draft',
                                                    })
                                                    setLayoutForm({
                                                        layout: 'novo_layout',
                                                        document_type: 'scanned_image',
                                                        schema_config_id: '',
                                                        confidence_threshold: '0.75',
                                                    })
                                                    setFields(DEFAULT_LANGEXTRACT_FIELDS)
                                                    setPrompt(DEFAULT_LANGEXTRACT_PROMPT)
                                                    setExamples([])
                                                    setReferenceReview({
                                                        quality: 'pending',
                                                        action: 'review_before_examples',
                                                        notes: '',
                                                    })
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
                                                <input
                                                    value={schemaForm.model_name}
                                                    onChange={(event) =>
                                                        setSchemaForm({ ...schemaForm, model_name: event.target.value })
                                                    }
                                                    className="input"
                                                    placeholder="Recibo de servico"
                                                />
                                            </Field>
                                            <Field label="Schema">
                                                <input
                                                    value={schemaForm.schema_id}
                                                    onChange={(event) =>
                                                        setSchemaForm({ ...schemaForm, schema_id: event.target.value })
                                                    }
                                                    className="input"
                                                    placeholder="recibo_servico"
                                                />
                                            </Field>
                                            <Field label="Versao">
                                                <input
                                                    value={schemaForm.version}
                                                    onChange={(event) =>
                                                        setSchemaForm({ ...schemaForm, version: event.target.value })
                                                    }
                                                    className="input"
                                                />
                                            </Field>
                                            <Field label="Tipo de documento">
                                                <select
                                                    value={schemaForm.document_type}
                                                    onChange={(event) => {
                                                        setSchemaForm({
                                                            ...schemaForm,
                                                            document_type: event.target.value,
                                                        })
                                                        setLayoutForm({
                                                            ...layoutForm,
                                                            document_type: event.target.value,
                                                        })
                                                    }}
                                                    className="input"
                                                >
                                                    <option value="scanned_image">Imagem/PDF escaneado</option>
                                                    <option value="digital_pdf">PDF textual</option>
                                                    <option value="handwritten_complex">Manuscrito complexo</option>
                                                </select>
                                            </Field>
                                            <Field label="Status">
                                                <select
                                                    value={schemaForm.status}
                                                    onChange={(event) =>
                                                        setSchemaForm({ ...schemaForm, status: event.target.value })
                                                    }
                                                    className="input"
                                                >
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
                                        <SchemaList schemas={schemas} onDeleted={onChanged} />
                                        <ConfigList
                                            title="Layouts existentes"
                                            items={layouts}
                                            primaryKey="layout"
                                            secondaryKey="document_type"
                                        />
                                    </div>
                                </div>
                            ) : null}

                            {activeTab === 'ocr' ? (
                                <ReferenceDocumentPanel
                                    selectedDocumentId={selectedDocumentId}
                                    onSelectDocument={setSelectedDocumentId}
                                    referenceDocument={referenceDocument}
                                    fields={fields}
                                    review={referenceReview}
                                    onReviewChange={setReferenceReview}
                                />
                            ) : null}

                            {activeTab === 'schema' ? (
                                <SchemaFieldsEditor fields={fields} onChange={setFields} schemaForm={schemaForm} />
                            ) : null}

                            {activeTab === 'instructions' ? (
                                <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                                    <Field label="Prompt controlado">
                                        <textarea
                                            value={prompt}
                                            onChange={(event) => setPrompt(event.target.value)}
                                            className="input min-h-[280px] font-mono"
                                        />
                                    </Field>
                                    <HintPanel
                                        title="Blocos prontos"
                                        items={PROMPT_HINTS}
                                        onUse={(hint) => setPrompt((current) => `${current}\n- ${hint}.`)}
                                    />
                                </div>
                            ) : null}

                            {activeTab === 'examples' ? (
                                <ExamplesEditor
                                    examples={examples}
                                    onChange={setExamples}
                                    referenceText={referenceDocument?.full_transcription || ''}
                                />
                            ) : null}

                            {activeTab === 'test' ? (
                                <div className="grid gap-4 xl:grid-cols-[minmax(320px,0.9fr)_minmax(360px,1.1fr)_minmax(320px,0.8fr)]">
                                    <DocumentPreview document={referenceDocument} />
                                    <HighlightedOcrText
                                        text={referenceDocument?.full_transcription || ''}
                                        fields={fields}
                                        examples={examples}
                                    />
                                    <Field label="Preview JSON">
                                        <textarea
                                            value={testOutput}
                                            onChange={(event) => setTestOutput(event.target.value)}
                                            className="input min-h-[520px] font-mono"
                                        />
                                    </Field>
                                </div>
                            ) : null}

                            {activeTab === 'rules' ? (
                                <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                                    <Field label="Regras de pos-processamento JSON">
                                        <textarea
                                            value={normalizationRules}
                                            onChange={(event) => setNormalizationRules(event.target.value)}
                                            className="input min-h-[300px] font-mono"
                                        />
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
                                        <pre className="max-h-[360px] overflow-auto rounded-md bg-zinc-950 p-3 text-xs text-zinc-50">
                                            {JSON.stringify(schemaDefinition, null, 2)}
                                        </pre>
                                        <button
                                            type="button"
                                            onClick={createSchema}
                                            disabled={!schemaForm.schema_id.trim()}
                                            className="primary-button mt-3"
                                        >
                                            Salvar schema LangExtract
                                        </button>
                                    </section>
                                    <section className="rounded-md border border-zinc-200 p-4">
                                        <div className="mb-3 text-sm font-semibold">Vincular layout ao schema</div>
                                        <div className="grid gap-3 md:grid-cols-2">
                                            <Field label="Layout">
                                                <input
                                                    value={layoutForm.layout}
                                                    onChange={(event) =>
                                                        setLayoutForm({ ...layoutForm, layout: event.target.value })
                                                    }
                                                    className="input"
                                                />
                                            </Field>
                                            <Field label="Tipo documento">
                                                <input
                                                    value={layoutForm.document_type}
                                                    onChange={(event) =>
                                                        setLayoutForm({
                                                            ...layoutForm,
                                                            document_type: event.target.value,
                                                        })
                                                    }
                                                    className="input"
                                                />
                                            </Field>
                                            <Field label="Schema">
                                                <select
                                                    value={layoutForm.schema_config_id}
                                                    onChange={(event) =>
                                                        setLayoutForm({
                                                            ...layoutForm,
                                                            schema_config_id: event.target.value,
                                                        })
                                                    }
                                                    className="input"
                                                >
                                                    <option value="">Selecionar</option>
                                                    {schemas.map((schema) => (
                                                        <option key={schema.id} value={schema.id}>
                                                            {schema.schema_id} {schema.version}
                                                        </option>
                                                    ))}
                                                </select>
                                            </Field>
                                            <Field label="Confianca minima">
                                                <input
                                                    value={layoutForm.confidence_threshold}
                                                    onChange={(event) =>
                                                        setLayoutForm({
                                                            ...layoutForm,
                                                            confidence_threshold: event.target.value,
                                                        })
                                                    }
                                                    className="input"
                                                />
                                            </Field>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={createLayout}
                                            disabled={!layoutForm.layout.trim() || !layoutForm.schema_config_id}
                                            className="primary-button mt-3"
                                        >
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
                    <OcrSettingsPanel settings={ocrSettings} onChange={setOcrSettings} onSave={saveOcrSettings} />
                ) : null}
                {activeSettingsArea === 'email' ? (
                    <EmailSettingsPanel
                        settings={emailSettings}
                        onChange={setEmailSettings}
                        onSave={saveEmailSettings}
                        onPoll={testEmailPoll}
                    />
                ) : null}
                {activeSettingsArea === 'whatsapp' ? <WhatsAppSettingsPanel onPoll={pollWhatsApp} /> : null}
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

function TabHelp({ tab }: { tab: string }) {
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

function OcrSettingsPanel({
    settings,
    onChange,
    onSave,
}: {
    settings: OcrSettingsForm
    onChange: React.Dispatch<React.SetStateAction<OcrSettingsForm>>
    onSave: () => void | Promise<unknown>
}) {
    const updateField = <K extends keyof OcrSettingsForm>(field: K, value: OcrSettingsForm[K]) => {
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
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Roteamento ativo</div>
                    <div className="space-y-3">
                        {activeOcrRoutes.map((route) => (
                            <div
                                key={route.classification}
                                className="rounded-md border border-zinc-200 bg-zinc-50 p-3"
                            >
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
                            <EngineSelect
                                value={settings.digital_pdf_engine}
                                onChange={(value) => updateField('digital_pdf_engine', value)}
                            />
                        </Field>
                        <Field label="Imagem/PDF escaneado">
                            <EngineSelect
                                value={settings.scanned_image_engine}
                                onChange={(value) => updateField('scanned_image_engine', value)}
                            />
                        </Field>
                        <Field label="Manuscrito complexo">
                            <EngineSelect
                                value={settings.handwritten_engine}
                                onChange={(value) => updateField('handwritten_engine', value)}
                            />
                        </Field>
                        <Field label="Fallback tecnico">
                            <EngineSelect
                                value={settings.technical_fallback_engine}
                                onChange={(value) => updateField('technical_fallback_engine', value)}
                            />
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
                                onChange={(event) =>
                                    updateField('retry_empty_text_enabled', event.target.value === 'enabled')
                                }
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
                        A chave OpenRouter continua no `.env` e nao e gravada aqui. PaddleOCR, EasyOCR, TrOCR,
                        LlamaParse e DeepSeek permanecem como codigo legado/opcional, mas nao fazem parte do setup
                        operacional atual.
                    </p>
                </section>
            </div>
        </div>
    )
}

function EngineSelect({ value, onChange }: { value?: string; onChange: (value: string) => void }) {
    return (
        <select className="input" value={value || 'docling'} onChange={(event) => onChange(event.target.value)}>
            <option value="docling">Docling</option>
            <option value="openrouter">OpenRouter</option>
            <option value="tesseract">Tesseract</option>
        </select>
    )
}

function engineLabel(value?: string): string {
    return (
        (
            {
                docling: 'Docling',
                openrouter: 'OpenRouter',
                tesseract: 'Tesseract',
            } as Record<string, string>
        )[value ?? ''] ||
        value ||
        '-'
    )
}

function EmailSettingsPanel({
    settings,
    onChange,
    onSave,
    onPoll,
}: {
    settings: EmailSettingsForm
    onChange: React.Dispatch<React.SetStateAction<EmailSettingsForm>>
    onSave: () => void | Promise<unknown>
    onPoll: () => void | Promise<unknown>
}) {
    const updateField = <K extends keyof EmailSettingsForm>(field: K, value: EmailSettingsForm[K]) => {
        onChange((current) => ({ ...current, [field]: value }))
    }

    return (
        <div className="space-y-4 p-4">
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
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Conta de captura</div>
                    <div className="grid gap-3 md:grid-cols-2">
                        <Field label="Provider">
                            <select
                                className="input"
                                value={settings.provider || 'imap'}
                                onChange={(event) => updateField('provider', event.target.value)}
                            >
                                <option value="imap">IMAP</option>
                                <option value="webhook">Webhook</option>
                                <option value="manual_test">Teste manual</option>
                            </select>
                        </Field>
                        <Field label="Ativo">
                            <select
                                className="input"
                                value={settings.is_active ? 'enabled' : 'disabled'}
                                onChange={(event) => updateField('is_active', event.target.value === 'enabled')}
                            >
                                <option value="enabled">Ativo</option>
                                <option value="disabled">Inativo</option>
                            </select>
                        </Field>
                        <Field label="Pasta monitorada">
                            <input
                                className="input"
                                value={settings.inbox_folder || ''}
                                onChange={(event) => updateField('inbox_folder', event.target.value)}
                            />
                        </Field>
                        <Field label="Host IMAP">
                            <input
                                className="input"
                                value={settings.imap_host || ''}
                                onChange={(event) => updateField('imap_host', event.target.value)}
                                placeholder="imap.exemplo.com"
                            />
                        </Field>
                        <Field label="Porta">
                            <input
                                className="input"
                                type="number"
                                min="1"
                                max="65535"
                                value={settings.imap_port}
                                onChange={(event) => updateField('imap_port', event.target.value)}
                            />
                        </Field>
                        <Field label="Usuario">
                            <input
                                className="input"
                                value={settings.username || ''}
                                onChange={(event) => updateField('username', event.target.value)}
                                placeholder="documentos@empresa.com"
                            />
                        </Field>
                        <Field label="Senha/app password">
                            <input
                                className="input"
                                type="password"
                                placeholder="Nao persistido por enquanto"
                                disabled
                            />
                        </Field>
                        <Field label="Webhook URL">
                            <input
                                className="input"
                                value={settings.webhook_url || ''}
                                onChange={(event) => updateField('webhook_url', event.target.value)}
                            />
                        </Field>
                    </div>
                </section>
                <section className="rounded-md border border-zinc-200 p-4">
                    <div className="mb-3 text-sm font-semibold">Regras de anexos</div>
                    <div className="space-y-3">
                        <Field label="Tipos aceitos">
                            <input
                                className="input"
                                value={settings.accepted_content_types || ''}
                                onChange={(event) => updateField('accepted_content_types', event.target.value)}
                            />
                        </Field>
                        <Field label="Tamanho maximo MB">
                            <input
                                className="input"
                                type="number"
                                min="1"
                                max="200"
                                value={settings.max_attachment_mb}
                                onChange={(event) => updateField('max_attachment_mb', event.target.value)}
                            />
                        </Field>
                        <Field label="Remetentes bloqueados">
                            <textarea
                                className="input min-h-[90px]"
                                value={settings.blocked_senders || ''}
                                onChange={(event) => updateField('blocked_senders', event.target.value)}
                                placeholder="um email por linha"
                            />
                        </Field>
                    </div>
                </section>
            </div>
        </div>
    )
}

function WhatsAppSettingsPanel({ onPoll }: { onPoll: () => void | Promise<unknown> }) {
    return (
        <div className="space-y-4 p-4">
            <ConfigIntro
                title="WhatsApp"
                text="Configure a recepcao via Twilio WhatsApp. Enquanto as credenciais finais nao estiverem disponiveis, os testes reais podem falhar sem bloquear o restante do desenvolvimento."
            />
            <div className="flex flex-wrap justify-end gap-2">
                <button
                    type="button"
                    onClick={onPoll}
                    className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                >
                    <RefreshCw size={16} aria-hidden="true" />
                    Processar arquivos do WhatsApp
                </button>
            </div>
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
                            <input
                                className="input"
                                defaultValue="application/pdf,image/jpeg,image/png,image/tiff,image/webp"
                            />
                        </Field>
                    </div>
                </section>
            </div>
        </div>
    )
}

function IntegrationSettingsPanel({
    settings,
    onChange,
    onSave,
}: {
    settings: IntegrationSettingsForm
    onChange: React.Dispatch<React.SetStateAction<IntegrationSettingsForm>>
    onSave: () => void | Promise<unknown>
}) {
    const updateField = <K extends keyof IntegrationSettingsForm>(field: K, value: IntegrationSettingsForm[K]) => {
        onChange((current) => ({ ...current, [field]: value }))
    }

    return (
        <div className="space-y-4 p-4">
            <ConfigIntro
                title="Integracoes"
                text="Configure o destino dos dados aprovados. Por enquanto o caminho intermediario e exportacao JSON; Superlogica fica preparado para quando houver acesso ao ambiente."
            />
            <div className="flex justify-end">
                <button
                    type="button"
                    onClick={onSave}
                    className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700"
                >
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
                                onChange={(event) =>
                                    updateField('approved_export_enabled', event.target.value === 'enabled')
                                }
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
                            <input
                                className="input"
                                type="password"
                                placeholder="Nao persistido por enquanto"
                                disabled
                            />
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

function ConfigIntro({ title, text }: { title: React.ReactNode; text: React.ReactNode }) {
    return (
        <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3">
            <div className="text-sm font-semibold text-sky-950">{title}</div>
            <div className="mt-1 text-sm leading-6 text-sky-800">{text}</div>
        </div>
    )
}

function ActiveTemplateHeader({
    schemaForm,
    layoutForm,
    activeLayout,
    onChangeModel,
}: {
    schemaForm: SchemaForm
    layoutForm: LayoutForm
    activeLayout?: LayoutConfig
    onChangeModel: () => void
}) {
    return (
        <div className="mb-4 rounded-md border border-zinc-200 bg-zinc-50 px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <div className="text-xs font-semibold uppercase text-zinc-500">Modelo ativo</div>
                    <div className="mt-1 text-sm font-semibold text-zinc-950">
                        {schemaForm.model_name || schemaForm.schema_id || 'Modelo sem nome'}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-600">
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">
                            schema: {schemaForm.schema_id || '-'} · {schemaForm.version || '-'}
                        </span>
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">
                            layout: {activeLayout?.layout || layoutForm.layout || '-'}
                        </span>
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">
                            tipo: {schemaForm.document_type || '-'}
                        </span>
                        <span className="rounded bg-white px-2 py-1 ring-1 ring-zinc-200">
                            status: {schemaForm.status || '-'}
                        </span>
                    </div>
                </div>
                <button
                    type="button"
                    onClick={onChangeModel}
                    className="h-9 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium hover:bg-zinc-100"
                >
                    Alterar modelo
                </button>
            </div>
        </div>
    )
}

function SettingsStepActions({
    activeTab,
    onSaveDraft,
    onNext,
}: {
    activeTab: string
    onSaveDraft: () => void | Promise<unknown>
    onNext: () => void | Promise<unknown>
}) {
    const currentIndex = SETTINGS_TABS.findIndex((tab) => tab.id === activeTab)
    const nextTab = SETTINGS_TABS[currentIndex + 1]
    return (
        <div className="mt-4 flex flex-wrap items-center justify-end gap-2 border-t border-zinc-200 pt-4">
            <button
                type="button"
                onClick={onSaveDraft}
                className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium hover:bg-zinc-100"
            >
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

function HintPanel({
    title,
    items,
    onUse = undefined,
}: {
    title: React.ReactNode
    items: string[]
    onUse?: (item: string) => void
}) {
    return (
        <aside className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
            <div className="text-sm font-semibold">{title}</div>
            <div className="mt-3 space-y-2">
                {items.map((item) => (
                    <div
                        key={item}
                        className="flex items-start justify-between gap-2 rounded border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-600"
                    >
                        <span>{item}</span>
                        {onUse ? (
                            <button
                                type="button"
                                onClick={() => onUse(item)}
                                className="shrink-0 rounded border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100"
                            >
                                Usar
                            </button>
                        ) : null}
                    </div>
                ))}
            </div>
        </aside>
    )
}

function ReferenceDocumentPanel({
    selectedDocumentId,
    onSelectDocument,
    referenceDocument,
    fields,
    review,
    onReviewChange,
}: {
    selectedDocumentId: string
    onSelectDocument: (id: string) => void
    referenceDocument: Document | null
    fields: SchemaField[]
    review: ReferenceReview
    onReviewChange: (review: ReferenceReview) => void
}) {
    // feature 009: o seletor de referência fica fora da paginação por tela
    // (Clarifications), mas a busca agora é server-side e carrega só a primeira
    // página (mais recentes) em vez de toda a base no cliente.
    const { search, setSearch, data } = useDocumentPage(undefined, {})

    return (
        <div className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-[360px_minmax(360px,1fr)_minmax(360px,1fr)]">
                <section className="rounded-md border border-zinc-200">
                    <div className="flex flex-col gap-2 border-b border-zinc-200 px-3 py-2">
                        <div className="text-sm font-semibold">Documento de referencia</div>
                        <SearchInput value={search} onChange={setSearch} placeholder="Buscar..." />
                    </div>
                    <div className="max-h-[520px] overflow-auto">
                        {data.results.map((document) => (
                            <button
                                key={document.id}
                                type="button"
                                onClick={() => onSelectDocument(document.id)}
                                className={`block w-full border-b border-zinc-100 px-3 py-2 text-left text-sm hover:bg-zinc-50 ${selectedDocumentId === document.id ? 'bg-zinc-100' : ''}`}
                            >
                                <div className="font-medium">{document.original_filename || document.id}</div>
                                <div className="mt-1 text-xs text-zinc-500">
                                    {document.document_type || '-'} · {document.channel || '-'}
                                </div>
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
                        <select
                            value={review.quality}
                            onChange={(event) => onReviewChange({ ...review, quality: event.target.value })}
                            className="input"
                        >
                            <option value="pending">Nao revisado</option>
                            <option value="matches">Confere com o documento</option>
                            <option value="minor_issues">Tem pequenas divergencias</option>
                            <option value="major_issues">Nao confere</option>
                        </select>
                    </Field>
                    <Field label="Acao recomendada">
                        <select
                            value={review.action}
                            onChange={(event) => onReviewChange({ ...review, action: event.target.value })}
                            className="input"
                        >
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

function DocumentPreview({ document }: { document: Document | null }) {
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">Original</div>
            {!document ? (
                <EmptyState icon={FileText} text="Selecione um documento." />
            ) : (
                // Carrega o arquivo como blob autenticado (contorna X-Frame-Options em produção).
                <DocumentBlobPreview
                    documentId={document.id}
                    contentType={document.content_type}
                    filename={document.original_filename}
                    frameClassName="h-[520px] w-full"
                />
            )}
        </section>
    )
}

function HighlightedOcrText({
    text,
    fields,
    examples,
}: {
    text?: string
    fields: SchemaField[]
    examples: SchemaExample[]
}) {
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

function SchemaFieldsEditor({
    fields,
    onChange,
    schemaForm,
}: {
    fields: SchemaField[]
    onChange: (fields: SchemaField[]) => void
    schemaForm: SchemaForm
}) {
    const updateField = (index: number, patch: Partial<SchemaField>) => {
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
                            Os campos abaixo pertencem ao schema definido na aba Setup. Ao salvar em Publicacao, eles
                            serao gravados nessa versao.
                        </div>
                    </div>
                </div>
            </section>
            <div className="rounded-md border border-zinc-200">
                <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                    <div className="text-sm font-semibold">Campos de saida</div>
                    <button
                        type="button"
                        onClick={() => onChange([...fields, { name: '', type: 'string', required: false, rule: '' }])}
                        className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100"
                    >
                        Adicionar
                    </button>
                </div>
                <div className="divide-y divide-zinc-100">
                    {fields.map((field, index) => (
                        <div
                            key={`${field.name}-${index}`}
                            className="grid gap-2 px-3 py-3 lg:grid-cols-[180px_140px_120px_1fr]"
                        >
                            <input
                                value={field.name}
                                onChange={(event) => updateField(index, { name: event.target.value })}
                                className="input"
                                placeholder="campo"
                            />
                            <select
                                value={field.type}
                                onChange={(event) => updateField(index, { type: event.target.value })}
                                className="input"
                            >
                                <option value="string">string</option>
                                <option value="decimal">decimal</option>
                                <option value="date">date</option>
                                <option value="cnpj">cnpj</option>
                                <option value="cpf">cpf</option>
                                <option value="enum">enum</option>
                            </select>
                            <label className="flex h-9 items-center gap-2 rounded-md border border-zinc-300 px-3 text-sm text-zinc-700">
                                <input
                                    type="checkbox"
                                    checked={field.required}
                                    onChange={(event) => updateField(index, { required: event.target.checked })}
                                />
                                Obrigatorio
                            </label>
                            <input
                                value={field.rule}
                                onChange={(event) => updateField(index, { rule: event.target.value })}
                                className="input"
                                placeholder="regra de extracao/normalizacao"
                            />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

function ExamplesEditor({
    examples,
    onChange,
    referenceText,
}: {
    examples: SchemaExample[]
    onChange: (examples: SchemaExample[]) => void
    referenceText?: string
}) {
    const updateExample = (index: number, patch: Partial<SchemaExample>) => {
        onChange(examples.map((example, exampleIndex) => (exampleIndex === index ? { ...example, ...patch } : example)))
    }

    return (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
            <section className="rounded-md border border-zinc-200">
                <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                    <div className="text-sm font-semibold">Few-shot anotados</div>
                    <button
                        type="button"
                        onClick={() => onChange([...examples, { field: '', expected: '', source: '' }])}
                        className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100"
                    >
                        Adicionar
                    </button>
                </div>
                <div className="divide-y divide-zinc-100">
                    {examples.map((example, index) => (
                        <div key={`${example.field}-${index}`} className="grid gap-2 px-3 py-3 md:grid-cols-3">
                            <input
                                value={example.field}
                                onChange={(event) => updateExample(index, { field: event.target.value })}
                                className="input"
                                placeholder="campo"
                            />
                            <input
                                value={example.expected}
                                onChange={(event) => updateExample(index, { expected: event.target.value })}
                                className="input"
                                placeholder="valor esperado"
                            />
                            <input
                                value={example.source}
                                onChange={(event) => updateExample(index, { source: event.target.value })}
                                className="input"
                                placeholder="trecho fonte"
                            />
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

const PROTECTED_SCHEMA_IDS = ['nota_fiscal_default', 'conta_agua_default']

function DeleteSchemaModal({
    schema,
    onClose,
    onDeleted,
}: {
    schema: SchemaConfig
    onClose: () => void
    onDeleted: () => void | Promise<unknown>
}) {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    if (schema.schema_id && PROTECTED_SCHEMA_IDS.includes(schema.schema_id)) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                <div className="w-full max-w-md rounded-lg border border-zinc-200 bg-white p-6 shadow-xl">
                    <div className="text-sm font-semibold text-zinc-900">Modelo protegido</div>
                    <p className="mt-2 text-sm text-zinc-600">
                        O modelo <span className="font-medium">{schema.schema_id}</span> é padrão do sistema e não pode
                        ser excluído.
                    </p>
                    <div className="mt-4 flex justify-end">
                        <button
                            type="button"
                            onClick={onClose}
                            className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium hover:bg-zinc-100"
                        >
                            Fechar
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    async function handleDelete() {
        setLoading(true)
        setError('')
        try {
            await api.delete(`/schema-configs/${schema.id}`)
            await onDeleted()
        } catch (err) {
            setError(readError(err, 'Erro ao excluir o modelo. Tente novamente.'))
            setLoading(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="w-full max-w-md rounded-lg border border-zinc-200 bg-white p-6 shadow-xl">
                <div className="text-sm font-semibold text-zinc-900">Excluir modelo</div>
                <p className="mt-2 text-sm text-zinc-600">
                    Tem certeza que deseja excluir o modelo <span className="font-medium">{schema.schema_id}</span>?
                    Esta ação não pode ser desfeita.
                </p>
                {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
                <div className="mt-4 flex justify-end gap-2">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={loading}
                        className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium hover:bg-zinc-100 disabled:opacity-50"
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={handleDelete}
                        disabled={loading}
                        className="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                    >
                        {loading ? 'Excluindo...' : 'Excluir'}
                    </button>
                </div>
            </div>
        </div>
    )
}

function SchemaList({ schemas, onDeleted }: { schemas: SchemaConfig[]; onDeleted: () => void | Promise<unknown> }) {
    const [targetSchema, setTargetSchema] = useState<SchemaConfig | null>(null)
    return (
        <>
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">Schemas existentes</div>
                {schemas.length === 0 ? (
                    <EmptyState icon={Settings} text="Nenhuma configuracao cadastrada." />
                ) : (
                    <div className="divide-y divide-zinc-100">
                        {schemas.map((schema) => (
                            <div key={schema.id} className="flex items-center justify-between px-4 py-3">
                                <div className="text-sm font-medium">{schema.schema_id}</div>
                                <button
                                    type="button"
                                    onClick={() => setTargetSchema(schema)}
                                    className="flex items-center gap-1 rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                                >
                                    <Trash2 size={12} />
                                    Excluir
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </section>
            {targetSchema && (
                <DeleteSchemaModal
                    schema={targetSchema}
                    onClose={() => setTargetSchema(null)}
                    onDeleted={async () => {
                        setTargetSchema(null)
                        await onDeleted()
                    }}
                />
            )}
        </>
    )
}

function ConfigList({
    title,
    items,
    primaryKey,
    secondaryKey,
}: {
    title: React.ReactNode
    items: Array<Record<string, unknown> & { id: React.Key }>
    primaryKey: string
    secondaryKey: string
}) {
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">{title}</div>
            {items.length === 0 ? (
                <EmptyState icon={Settings} text="Nenhuma configuracao cadastrada." />
            ) : (
                <div className="divide-y divide-zinc-100">
                    {items.map((item) => (
                        <div key={item.id} className="px-4 py-3">
                            <div className="text-sm font-medium">{String(item[primaryKey] ?? '')}</div>
                            <div className="mt-1 text-xs text-zinc-500">{String(item[secondaryKey] ?? '')}</div>
                        </div>
                    ))}
                </div>
            )}
        </section>
    )
}

function viewTitle(view: ActiveView | undefined): string {
    return NAV_ITEMS.find((item) => item.id === view)?.label ?? 'DocuParse'
}

function buildLangExtractDefinition({
    schemaForm,
    fields,
    prompt,
    examples,
    normalizationRules,
    referenceReview,
    referenceDocument,
}: {
    schemaForm: SchemaForm
    fields: SchemaField[]
    prompt: string
    examples: SchemaExample[]
    normalizationRules: string
    referenceReview: ReferenceReview
    referenceDocument: Document | null
}) {
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
        fields: fields
            .filter((field) => field.name.trim())
            .map((field) => ({
                name: field.name.trim(),
                type: field.type,
                required: Boolean(field.required),
                rule: field.rule,
            })),
        prompt: {
            instructions: prompt,
            guardrails: PROMPT_HINTS,
        },
        examples: examples.filter(
            (example) => example.field.trim() || example.expected.trim() || example.source.trim(),
        ),
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

function buildLangExtractPreview(text: string, fields: SchemaField[]): string {
    const output: Record<string, unknown> = {}
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

function findLikelySourceLine(text: string, fieldName: string): string {
    if (!text || !fieldName) {
        return ''
    }
    const normalizedField = normalizeSearchText(fieldName).replaceAll('_', ' ')
    return text.split(/\r?\n/).find((line) => normalizeSearchText(line).includes(normalizedField)) || ''
}

function renderHighlightedText(text: string, highlights: string[]): React.ReactNode {
    const terms = [...new Set(highlights.map((term) => term.trim()).filter((term) => term.length > 2))]
    if (terms.length === 0) {
        return text
    }

    const pattern = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'gi')
    return text.split(pattern).map((part, index) => {
        const isHighlighted = terms.some((term) => normalizeSearchText(term) === normalizeSearchText(part))
        return isHighlighted ? (
            <mark key={`${part}-${index}`} className="rounded bg-amber-100 px-0.5 text-amber-950">
                {part}
            </mark>
        ) : (
            <React.Fragment key={`${part}-${index}`}>{part}</React.Fragment>
        )
    })
}

function normalizeSearchText(value: unknown): string {
    return String(value || '')
        .trim()
        .toLowerCase()
}

function escapeRegExp(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// ─── User Management Screen ───────────────────────────────────────────────────

interface AdminRoleRef {
    id: string
    name: string
}

interface AdminUser {
    id: string
    name: string
    email: string
    role?: AdminRoleRef | null
    is_active?: boolean
    [key: string]: unknown
}

interface AdminPermission {
    code: string
    name?: string
    description?: string
    [key: string]: unknown
}

interface AdminRole {
    id: string
    name: string
    permissions?: Array<AdminPermission | string>
    users_count?: number
    [key: string]: unknown
}

export function GerenciarUsuarios() {
    const [users, setUsers] = useState<AdminUser[]>([])
    const [roles, setRoles] = useState<AdminRole[]>([])
    const [loading, setLoading] = useState(true)
    const [modal, setModal] = useState<{ mode: 'create' | 'edit'; user?: AdminUser } | null>(null)
    const [form, setForm] = useState({ name: '', email: '', password: '', role_id: '' })
    const [error, setError] = useState('')

    const load = async () => {
        setLoading(true)
        const [u, r] = await Promise.all([api.get<AdminUser[]>('/users'), api.get<AdminRole[]>('/roles')])
        setUsers(u.data)
        setRoles(r.data)
        setLoading(false)
    }

    useEffect(() => {
        load()
    }, [])

    const openCreate = () => {
        setForm({ name: '', email: '', password: '', role_id: '' })
        setModal({ mode: 'create' })
        setError('')
    }
    const openEdit = (u: AdminUser) => {
        setForm({ name: u.name, email: u.email, password: '', role_id: u.role?.id || '' })
        setModal({ mode: 'edit', user: u })
        setError('')
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        try {
            if (modal?.mode === 'create') {
                await api.post('/users', form)
            } else {
                const patch = { name: form.name, email: form.email, role_id: form.role_id || null }
                await api.patch(`/users/${modal?.user?.id}`, patch)
            }
            setModal(null)
            load()
        } catch (err) {
            const data = asApiError(err).response?.data
            setError(data?.detail || data?.email?.[0] || 'Erro ao salvar.')
        }
    }

    const toggleActive = async (user: AdminUser) => {
        try {
            await api.patch(`/users/${user.id}`, { is_active: !user.is_active })
            load()
        } catch (err) {
            alert(asApiError(err).response?.data?.detail || 'Erro ao alterar status.')
        }
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Usuários</h2>
                <button
                    onClick={openCreate}
                    className="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white hover:bg-zinc-700"
                >
                    Novo Usuário
                </button>
            </div>
            {loading ? (
                <div className="text-sm text-zinc-500">Carregando...</div>
            ) : (
                <table className="w-full text-sm border border-zinc-200 rounded-md overflow-hidden">
                    <thead className="bg-zinc-50 text-zinc-600">
                        <tr>
                            {['Nome', 'E-mail', 'Role', 'Status', 'Ações'].map((h) => (
                                <th key={h} className="px-3 py-2 text-left font-medium">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {users.map((u) => (
                            <tr key={u.id} className="border-t border-zinc-100">
                                <td className="px-3 py-2">{u.name}</td>
                                <td className="px-3 py-2 text-zinc-500">{u.email}</td>
                                <td className="px-3 py-2">{u.role?.name || '—'}</td>
                                <td className="px-3 py-2">
                                    <span
                                        className={`rounded-full px-2 py-0.5 text-xs ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-zinc-100 text-zinc-500'}`}
                                    >
                                        {u.is_active ? 'Ativo' : 'Inativo'}
                                    </span>
                                </td>
                                <td className="px-3 py-2 flex gap-2">
                                    <button
                                        onClick={() => openEdit(u)}
                                        className="text-xs text-zinc-600 hover:underline"
                                    >
                                        Editar
                                    </button>
                                    <button
                                        onClick={() => toggleActive(u)}
                                        className="text-xs text-zinc-600 hover:underline"
                                    >
                                        {u.is_active ? 'Desativar' : 'Ativar'}
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
            {modal && (
                <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-lg">
                        <h3 className="text-lg font-semibold mb-4">
                            {modal.mode === 'create' ? 'Novo Usuário' : 'Editar Usuário'}
                        </h3>
                        {error && <div className="mb-3 text-sm text-red-600">{error}</div>}
                        <form onSubmit={handleSubmit} className="space-y-3">
                            <input
                                value={form.name}
                                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                                placeholder="Nome"
                                required
                                className="w-full border border-zinc-300 rounded-md px-3 py-2 text-sm"
                            />
                            <input
                                type="email"
                                value={form.email}
                                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                                placeholder="E-mail"
                                required
                                className="w-full border border-zinc-300 rounded-md px-3 py-2 text-sm"
                            />
                            {modal.mode === 'create' && (
                                <input
                                    type="password"
                                    value={form.password}
                                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                                    placeholder="Senha (mín. 8 chars)"
                                    required
                                    minLength={8}
                                    className="w-full border border-zinc-300 rounded-md px-3 py-2 text-sm"
                                />
                            )}
                            <select
                                value={form.role_id}
                                onChange={(e) => setForm((f) => ({ ...f, role_id: e.target.value }))}
                                required
                                className="w-full border border-zinc-300 rounded-md px-3 py-2 text-sm"
                            >
                                <option value="">Selecionar role...</option>
                                {roles.map((r) => (
                                    <option key={r.id} value={r.id}>
                                        {r.name}
                                    </option>
                                ))}
                            </select>
                            <div className="flex gap-2 justify-end pt-2">
                                <button
                                    type="button"
                                    onClick={() => setModal(null)}
                                    className="px-4 py-2 text-sm border border-zinc-300 rounded-md"
                                >
                                    Cancelar
                                </button>
                                <button type="submit" className="px-4 py-2 text-sm bg-zinc-900 text-white rounded-md">
                                    Salvar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}

// ─── Role Management Screen ───────────────────────────────────────────────────

export function GerenciarRoles() {
    const [roles, setRoles] = useState<AdminRole[]>([])
    const [perms, setPerms] = useState<AdminPermission[]>([])
    const [loading, setLoading] = useState(true)
    const [modal, setModal] = useState<{ mode: 'create' | 'edit'; role?: AdminRole } | null>(null)
    const [form, setForm] = useState<{ name: string; permission_codes: string[] }>({ name: '', permission_codes: [] })
    const [error, setError] = useState('')

    const load = async () => {
        setLoading(true)
        const [r, p] = await Promise.all([api.get<AdminRole[]>('/roles'), api.get<AdminPermission[]>('/permissions')])
        setRoles(r.data)
        setPerms(p.data)
        setLoading(false)
    }

    useEffect(() => {
        load()
    }, [])

    const openCreate = () => {
        setForm({ name: '', permission_codes: [] })
        setModal({ mode: 'create' })
        setError('')
    }
    const openEdit = (r: AdminRole) => {
        setForm({
            name: r.name,
            permission_codes: (r.permissions || []).map((p) => (typeof p === 'string' ? p : p.code)),
        })
        setModal({ mode: 'edit', role: r })
        setError('')
    }

    const togglePerm = (code: string) =>
        setForm((f) => ({
            ...f,
            permission_codes: f.permission_codes.includes(code)
                ? f.permission_codes.filter((c) => c !== code)
                : [...f.permission_codes, code],
        }))

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        try {
            if (modal?.mode === 'create') {
                await api.post('/roles', form)
            } else {
                await api.patch(`/roles/${modal?.role?.id}`, form)
            }
            setModal(null)
            load()
        } catch (err) {
            const data = asApiError(err).response?.data
            setError(data?.detail || data?.permission_codes?.[0] || 'Erro ao salvar.')
        }
    }

    const handleDelete = async (role: AdminRole) => {
        if (!window.confirm(`Remover role "${role.name}"?`)) return
        try {
            await api.delete(`/roles/${role.id}`)
            load()
        } catch (err) {
            alert(asApiError(err).response?.data?.detail || 'Erro ao remover.')
        }
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Roles e Permissões</h2>
                <button
                    onClick={openCreate}
                    className="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white hover:bg-zinc-700"
                >
                    Nova Role
                </button>
            </div>
            {loading ? (
                <div className="text-sm text-zinc-500">Carregando...</div>
            ) : (
                <table className="w-full text-sm border border-zinc-200 rounded-md overflow-hidden">
                    <thead className="bg-zinc-50 text-zinc-600">
                        <tr>
                            {['Nome', 'Permissões', 'Usuários', 'Ações'].map((h) => (
                                <th key={h} className="px-3 py-2 text-left font-medium">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {roles.map((r) => (
                            <tr key={r.id} className="border-t border-zinc-100">
                                <td className="px-3 py-2 font-medium">{r.name}</td>
                                <td className="px-3 py-2 text-zinc-500 text-xs">
                                    {(r.permissions || [])
                                        .map((p) => (typeof p === 'string' ? p : p.description || p.code))
                                        .join(', ')}
                                </td>
                                <td className="px-3 py-2">{r.users_count}</td>
                                <td className="px-3 py-2 flex gap-2">
                                    <button
                                        onClick={() => openEdit(r)}
                                        className="text-xs text-zinc-600 hover:underline"
                                    >
                                        Editar
                                    </button>
                                    <button
                                        onClick={() => handleDelete(r)}
                                        className="text-xs text-red-600 hover:underline"
                                    >
                                        Remover
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
            {modal && (
                <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-lg">
                        <h3 className="text-lg font-semibold mb-4">
                            {modal.mode === 'create' ? 'Nova Role' : 'Editar Role'}
                        </h3>
                        {error && <div className="mb-3 text-sm text-red-600">{error}</div>}
                        <form onSubmit={handleSubmit} className="space-y-3">
                            <input
                                value={form.name}
                                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                                placeholder="Nome da role"
                                required
                                className="w-full border border-zinc-300 rounded-md px-3 py-2 text-sm"
                            />
                            <div>
                                <div className="mb-2 text-sm font-medium text-zinc-700">Permissões</div>
                                <div className="grid grid-cols-2 gap-2">
                                    {perms.map((p) => (
                                        <label key={p.code} className="flex items-center gap-2 text-sm cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={form.permission_codes.includes(p.code)}
                                                onChange={() => togglePerm(p.code)}
                                                className="rounded"
                                            />
                                            {p.description}
                                        </label>
                                    ))}
                                </div>
                            </div>
                            <div className="flex gap-2 justify-end pt-2">
                                <button
                                    type="button"
                                    onClick={() => setModal(null)}
                                    className="px-4 py-2 text-sm border border-zinc-300 rounded-md"
                                >
                                    Cancelar
                                </button>
                                <button type="submit" className="px-4 py-2 text-sm bg-zinc-900 text-white rounded-md">
                                    Salvar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}

