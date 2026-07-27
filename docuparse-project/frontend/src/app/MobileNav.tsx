import { PermissionGuard } from '../modules/auth'
import type { ActiveView } from '../types'
import { NAV_ITEMS } from './navigation'
import { NavButton } from './NavButton'

export function MobileNav({ activeView }: { activeView: ActiveView | undefined }) {
    return (
        <div className="border-b border-zinc-200 bg-white px-2 py-2 md:hidden">
            <div className="flex gap-1 overflow-x-auto">
                {NAV_ITEMS.map((item) => (
                    <PermissionGuard key={item.id} code={item.permission}>
                        <NavButton item={item} active={activeView === item.id} compact />
                    </PermissionGuard>
                ))}
            </div>
        </div>
    )
}
