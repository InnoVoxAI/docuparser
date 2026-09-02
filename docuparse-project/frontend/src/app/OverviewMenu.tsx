import { useState } from 'react'
import { Link, NavLink } from 'react-router'
import { Building2, Menu as MenuIcon, X } from 'lucide-react'
import { PermissionGuard } from '../modules/auth'
import { NAV_ITEMS, navPath } from './navigation'

const SECTION_TABS = [
    { to: '/', label: 'Processos' },
    { to: '/stats', label: 'Estatísticas' },
]

/** As telas de processos (`/` e `/stats`) não têm cabeçalho nem sidebar — só o
 * conteúdo. Este botão flutuante no canto guarda a troca de seção, o acesso às
 * demais telas e o logout, fora do caminho visual. */
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

    return (
        <div className="fixed right-3 top-3 z-30 md:right-5 md:top-5">
            <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                aria-expanded={open}
                aria-label={open ? 'Fechar menu' : 'Abrir menu'}
                className="flex h-9 w-9 items-center justify-center rounded-md border border-zinc-200 bg-white text-zinc-600 shadow-sm hover:bg-zinc-100"
            >
                <MenuIcon size={18} aria-hidden="true" />
            </button>

            <div
                hidden={!open}
                className="absolute right-0 mt-2 w-56 rounded-lg border border-zinc-200 bg-white p-2 shadow-lg"
            >
                <div className="flex items-center justify-between px-2 py-1">
                    <span className="text-sm font-semibold text-zinc-900">{userName || 'Sessão'}</span>
                    <button
                        type="button"
                        onClick={() => setOpen(false)}
                        aria-label="Fechar"
                        className="text-zinc-400 hover:text-zinc-700"
                    >
                        <X size={16} aria-hidden="true" />
                    </button>
                </div>
                {currentTenant ? (
                    <div className="mx-2 mb-1 inline-flex items-center gap-1 rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-600">
                        <Building2 size={10} aria-hidden="true" />
                        {currentTenant}
                    </div>
                ) : null}

                <nav aria-label="Seções" className="mt-1 flex flex-col">
                    {SECTION_TABS.map((tab) => (
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
                        </NavLink>
                    ))}
                </nav>

                <div className="my-1 border-t border-zinc-100" />

                <nav aria-label="Outras telas" className="flex flex-col">
                    {NAV_ITEMS.map((item) => (
                        <PermissionGuard key={item.id} code={item.permission}>
                            <Link
                                to={navPath(item.id)}
                                onClick={() => setOpen(false)}
                                className="rounded-md px-2 py-1.5 text-sm font-medium text-zinc-600 hover:bg-zinc-100"
                            >
                                {item.label}
                            </Link>
                        </PermissionGuard>
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
