import { useState } from 'react'
import { NavLink } from 'react-router'
import { Building2, Menu as MenuIcon, X } from 'lucide-react'
import { useAuth } from '../modules/auth'
import { pendingTotal, useImportOverview } from '../modules/registry'

const SECTION_TABS = [
    { to: '/', label: 'Processos', permission: undefined },
    { to: '/stats', label: 'Estatísticas', permission: undefined },
    { to: '/registry', label: 'Cadastros', permission: 'inbox.view' },
    { to: '/registry-import', label: 'Confirmar importação', permission: 'inbox.view' },
    { to: '/integrations', label: 'Integrações', permission: 'models.edit' },
]

/** As telas de processos e de cadastros (`/`, `/stats`, `/registry`,
 * `/registry-import`, `/integrations`) não têm cabeçalho nem sidebar — só o conteúdo. Este botão
 * flutuante no canto guarda a troca de seção, o acesso às Integrações e o
 * logout, fora do caminho visual. Mostra também o usuário logado. */
export function OverviewMenu({
    userName,
    currentTenant,
    onLogout,
}: {
    userName: string | undefined
    currentTenant: string | null
    onLogout: () => void
}) {
    const [open, setOpen] = useState(false)
    const { hasPermission } = useAuth()
    const tabs = SECTION_TABS.filter((tab) => !tab.permission || hasPermission(tab.permission))
    // Propostas aguardando o analista: um ponto no botão e o número no item de confirmação.
    const overview = useImportOverview({ enabled: hasPermission('inbox.view') })
    const pending = pendingTotal(overview.data)

    return (
        <div className="fixed right-3 top-3 z-30 md:right-5 md:top-5">
            <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                aria-expanded={open}
                aria-label={open ? 'Fechar menu' : 'Abrir menu'}
                className="relative flex h-9 w-9 items-center justify-center rounded-md border border-zinc-200 bg-white text-zinc-600 shadow-sm hover:bg-zinc-100"
            >
                <MenuIcon size={18} aria-hidden="true" />
                {pending > 0 && !open ? (
                    <span
                        aria-hidden="true"
                        className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-amber-500 ring-2 ring-white"
                    />
                ) : null}
            </button>

            <div
                hidden={!open}
                className="absolute right-0 mt-2 w-52 rounded-lg border border-zinc-200 bg-white p-2 shadow-lg"
            >
                <div className="flex items-start justify-between gap-2 px-2 py-1">
                    <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-zinc-900">{userName || 'Sessão'}</div>
                        {currentTenant ? (
                            <div className="mt-0.5 inline-flex items-center gap-1 rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-600">
                                <Building2 size={10} aria-hidden="true" />
                                {currentTenant}
                            </div>
                        ) : null}
                    </div>
                    <button
                        type="button"
                        onClick={() => setOpen(false)}
                        aria-label="Fechar"
                        className="shrink-0 text-zinc-400 hover:text-zinc-700"
                    >
                        <X size={16} aria-hidden="true" />
                    </button>
                </div>

                <div className="my-1 border-t border-zinc-100" />

                <nav aria-label="Seções" className="flex flex-col">
                    {tabs.map((tab) => (
                        <NavLink
                            key={tab.to}
                            to={tab.to}
                            end
                            onClick={() => setOpen(false)}
                            className={({ isActive }) =>
                                `rounded-md px-2 py-1.5 text-sm font-medium ${
                                    isActive ? 'bg-zinc-900 text-white' : 'text-zinc-700 hover:bg-zinc-100'
                                }`
                            }
                        >
                            {tab.label}
                            {tab.to === '/registry-import' && pending > 0 ? (
                                <span className="ml-2 rounded-full bg-amber-100 px-1.5 text-xs font-semibold text-amber-800">
                                    {pending}
                                </span>
                            ) : null}
                        </NavLink>
                    ))}
                </nav>

                <div className="my-1 border-t border-zinc-100" />

                <button
                    type="button"
                    onClick={onLogout}
                    className="w-full rounded-md px-2 py-1.5 text-left text-sm font-medium text-zinc-600 hover:bg-zinc-100"
                >
                    Sair
                </button>
            </div>
        </div>
    )
}
