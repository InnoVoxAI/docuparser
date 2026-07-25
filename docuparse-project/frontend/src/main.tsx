import React, { useCallback, useEffect, useState } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router'
import {
    AlertTriangle,
    Building2,
    Check,
    ChevronDown,
    ClipboardCheck,
    Copy,
    Inbox,
    LayoutDashboard,
    RefreshCw,
    Settings,
    Upload,
    Users,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import './index.css'
import { Alert } from './shared/components'
import { readError } from './shared/utils'
import { api, adminApi } from './shared/lib/http'
import { useAuth, PermissionGuard } from './modules/auth'
import { RejectedDocumentModal, useDocumentMutations } from './modules/documents'
import type { AdminRole } from './modules/admin'
import type { Tenant, Document, ActiveView } from './types'

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
 * Estado/handlers de nível de app (documento selecionado/ações de documento)
 * hoje mantidos aqui porque as telas que os consomem (Dashboard, Inbox, etc.)
 * ainda não foram extraídas para `modules/documents` (Fase 4d) — quando
 * forem, isto vira TanStack Query e este contexto desaparece.
 * `schemas`/`layouts` saíram daqui na Fase 4f/T036-T040 (decisão #5): agora
 * vêm de `useSchemasQuery`/`useLayoutsQuery` (`modules/settings`), consumidos
 * diretamente por quem precisa (`ValidationRoute`, `SettingsView`).
 */
export interface AppOutletContext {
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

function viewTitle(view: ActiveView | undefined): string {
    return NAV_ITEMS.find((item) => item.id === view)?.label ?? 'DocuParse'
}
