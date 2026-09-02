import { Link, NavLink } from 'react-router'
import { Building2 } from 'lucide-react'
import { PermissionGuard } from '../modules/auth'
import { NAV_ITEMS, navPath } from './navigation'

const SECTION_TABS = [
    { to: '/', label: 'Processos' },
    { to: '/stats', label: 'Estatísticas' },
]

/** Cabeçalho enxuto das telas de processos (Visão Geral + Estatísticas): sem a
 * sidebar de navegação — só a marca, as abas de seção, um acesso leve às demais
 * telas e a sessão. Reduz a carga visual das telas mais usadas. */
export function OverviewTopBar({
    userName,
    currentTenant,
    onLogout,
}: {
    userName: string | undefined
    currentTenant: string | null
    onLogout: () => void
}) {
    return (
        <header className="border-b border-zinc-200 bg-white">
            <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3 md:px-6">
                <div className="flex items-center gap-4">
                    <Link to="/" className="text-lg font-semibold text-zinc-900">
                        DocuParse
                    </Link>
                    {currentTenant ? (
                        <span className="inline-flex items-center gap-1 rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-600">
                            <Building2 size={10} aria-hidden="true" />
                            {currentTenant}
                        </span>
                    ) : null}
                    <nav aria-label="Seções" className="flex items-center gap-1">
                        {SECTION_TABS.map((tab) => (
                            <NavLink
                                key={tab.to}
                                to={tab.to}
                                end
                                className={({ isActive }) =>
                                    `rounded-md px-2.5 py-1 text-sm font-medium ${
                                        isActive
                                            ? 'bg-zinc-900 text-white'
                                            : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900'
                                    }`
                                }
                            >
                                {tab.label}
                            </NavLink>
                        ))}
                    </nav>
                </div>
                <div className="flex items-center gap-3">
                    <nav aria-label="Navegação" className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        {NAV_ITEMS.map((item) => (
                            <PermissionGuard key={item.id} code={item.permission}>
                                <Link
                                    to={navPath(item.id)}
                                    className="text-sm font-medium text-zinc-500 hover:text-zinc-900"
                                >
                                    {item.label}
                                </Link>
                            </PermissionGuard>
                        ))}
                    </nav>
                    <span className="text-zinc-300" aria-hidden="true">
                        |
                    </span>
                    <span className="text-sm text-zinc-500">{userName || 'Sessão'}</span>
                    <button
                        type="button"
                        onClick={onLogout}
                        className="text-sm font-medium text-zinc-500 hover:text-zinc-900"
                    >
                        Sair
                    </button>
                </div>
            </div>
        </header>
    )
}
