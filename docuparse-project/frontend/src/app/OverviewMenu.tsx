import { useState } from 'react'
import { NavLink } from 'react-router'
import { Building2, Menu as MenuIcon, X } from 'lucide-react'

const SECTION_TABS = [
    { to: '/', label: 'Processos' },
    { to: '/stats', label: 'Estatísticas' },
]

/** As telas de processos (`/` e `/stats`) não têm cabeçalho nem sidebar — só o
 * conteúdo. Este botão flutuante no canto guarda a troca de seção e o logout,
 * fora do caminho visual. Mostra também o usuário logado. */
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
