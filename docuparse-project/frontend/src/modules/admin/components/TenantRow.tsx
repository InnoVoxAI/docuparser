import { Fragment } from 'react'
import { ChevronDown, Users } from 'lucide-react'
import type { Tenant } from '../../../types'
import { CopySlugButton } from './CopySlugButton'
import { TenantUsersPanel } from './TenantUsersPanel'

export function TenantRow({
    tenant,
    currentTenant,
    expanded,
    switching,
    switchError,
    toggleError,
    onToggleExpand,
    onSwitch,
    onToggle,
}: {
    tenant: Tenant
    currentTenant: string | null
    expanded: boolean
    switching: boolean
    switchError?: string
    toggleError?: string
    onToggleExpand: () => void
    onSwitch: () => void
    onToggle: () => void
}) {
    return (
        <Fragment>
            <tr className={`border-b border-zinc-100 hover:bg-zinc-50 ${expanded ? 'bg-zinc-50' : ''}`}>
                <td className="px-4 py-3 font-mono text-xs text-zinc-700">
                    <span className="inline-flex items-center gap-0.5">
                        {tenant.slug}
                        <CopySlugButton slug={tenant.slug} />
                        {currentTenant === tenant.slug ? (
                            <span className="ml-1.5 rounded bg-blue-100 px-1 py-0.5 text-blue-700 text-[10px] font-medium not-mono">
                                atual
                            </span>
                        ) : null}
                    </span>
                </td>
                <td className="px-4 py-3 text-zinc-800">{tenant.name}</td>
                <td className="px-4 py-3">
                    <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${tenant.is_active ? 'bg-green-100 text-green-700' : 'bg-zinc-100 text-zinc-500'}`}
                    >
                        {tenant.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                </td>
                <td className="px-4 py-3 text-zinc-500">{new Date(tenant.created_at).toLocaleDateString('pt-BR')}</td>
                <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center justify-end gap-1.5">
                        <button
                            type="button"
                            onClick={onSwitch}
                            disabled={switching || !tenant.is_active}
                            className="rounded px-2 py-1 text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-40"
                        >
                            {switching ? '...' : 'Alternar'}
                        </button>
                        <button
                            type="button"
                            onClick={onToggleExpand}
                            className="inline-flex items-center gap-0.5 rounded px-2 py-1 text-xs font-medium bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
                        >
                            <Users size={11} />
                            Usuários
                            <ChevronDown size={11} className={`transition-transform ${expanded ? 'rotate-180' : ''}`} />
                        </button>
                        <button
                            type="button"
                            onClick={onToggle}
                            className={`rounded px-2 py-1 text-xs font-medium ${tenant.is_active ? 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200' : 'bg-green-50 text-green-700 hover:bg-green-100'}`}
                        >
                            {tenant.is_active ? 'Desativar' : 'Ativar'}
                        </button>
                        {toggleError || switchError ? (
                            <span className="w-full text-right text-xs text-red-600">{toggleError || switchError}</span>
                        ) : null}
                    </div>
                </td>
            </tr>
            {expanded ? (
                <tr>
                    <td colSpan={5} className="p-0">
                        <TenantUsersPanel slug={tenant.slug} currentTenant={currentTenant} />
                    </td>
                </tr>
            ) : null}
        </Fragment>
    )
}
