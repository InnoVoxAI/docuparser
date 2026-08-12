import { Link } from 'react-router'
import { navPath, type NavItem } from './navigation'

export function NavButton({ item, active, compact = false }: { item: NavItem; active: boolean; compact?: boolean }) {
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
