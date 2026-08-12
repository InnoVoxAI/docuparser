import { Building2 } from 'lucide-react'
import { PermissionGuard } from '../modules/auth'
import type { ActiveView } from '../types'
import { NAV_ITEMS } from './navigation'
import { NavButton } from './NavButton'

export function AppSidebar({
    userName,
    currentTenant,
    activeView,
    onLogout,
}: {
    userName: string | undefined
    currentTenant: string | null
    activeView: ActiveView | undefined
    onLogout: () => void
}) {
    return (
        <aside className="hidden w-64 shrink-0 border-r border-zinc-200 bg-white md:block">
            <div className="border-b border-zinc-200 px-5 py-5">
                <div className="text-lg font-semibold">DocuParse</div>
                <div className="mt-1 text-xs text-zinc-500">{userName || 'Operacao de documentos'}</div>
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
                    onClick={onLogout}
                    className="flex w-full h-9 items-center gap-2 rounded-md px-3 text-sm font-medium text-zinc-600 hover:bg-zinc-100"
                >
                    Sair
                </button>
            </div>
        </aside>
    )
}
