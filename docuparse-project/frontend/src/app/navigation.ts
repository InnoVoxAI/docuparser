import { AlertTriangle, Building2, ClipboardCheck, Inbox, LayoutDashboard, Settings, Upload } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ActiveView } from '../types'
import { navPath } from '../shared/utils'

export { navPath }

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
    { id: 'validation', label: 'Validação', icon: ClipboardCheck, permission: 'documents.validate' },
    { id: 'operations', label: 'Operações', icon: AlertTriangle, permission: 'operations.access' },
    { id: 'settings', label: 'Configurações', icon: Settings, permission: 'roles.manage' },
    { id: 'users', label: 'Usuários', icon: Settings, permission: 'users.manage' },
    { id: 'roles', label: 'Roles', icon: Settings, permission: 'roles.manage' },
    { id: 'tenants', label: 'Tenants', icon: Building2, permission: 'tenants.manage' },
]

export function activeViewForPath(pathname: string): ActiveView | undefined {
    return NAV_ITEMS.find((item) => navPath(item.id) === pathname)?.id
}

export function viewTitle(view: ActiveView | undefined): string {
    return NAV_ITEMS.find((item) => item.id === view)?.label ?? 'DocuParse'
}
