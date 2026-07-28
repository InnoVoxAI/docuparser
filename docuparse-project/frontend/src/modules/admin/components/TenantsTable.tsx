import type { Tenant } from '../../../types'
import { TenantRow } from './TenantRow'

export function TenantsTable({
    tenants,
    currentTenant,
    expandedSlug,
    switchingSlug,
    switchError,
    toggleError,
    onToggleExpand,
    onSwitch,
    onToggle,
}: {
    tenants: Tenant[]
    currentTenant: string | null
    expandedSlug: string | null
    switchingSlug: string | null
    switchError: Record<string, string>
    toggleError: Record<string, string>
    onToggleExpand: (slug: string) => void
    onSwitch: (slug: string) => void
    onToggle: (slug: string, currentActive: boolean) => void
}) {
    return (
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
                        <TenantRow
                            key={t.slug}
                            tenant={t}
                            currentTenant={currentTenant}
                            expanded={expandedSlug === t.slug}
                            switching={switchingSlug === t.slug}
                            switchError={switchError[t.slug]}
                            toggleError={toggleError[t.slug]}
                            onToggleExpand={() => onToggleExpand(t.slug)}
                            onSwitch={() => onSwitch(t.slug)}
                            onToggle={() => onToggle(t.slug, t.is_active)}
                        />
                    ))}
                </tbody>
            </table>
        </div>
    )
}
