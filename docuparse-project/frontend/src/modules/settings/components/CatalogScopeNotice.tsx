import { AlertTriangle, Lock } from 'lucide-react'

/**
 * Aviso de escopo do catálogo de modelos de extração (spec 018): schemas e
 * layouts são GLOBAIS — uma única cópia compartilhada por todos os tenants.
 *
 * - `canManage` (`tenants.manage`): pode editar, mas a alteração afeta todos os
 *   tenants — aviso de atenção.
 * - sem permissão: acesso somente leitura, gestão restrita ao operador de
 *   plataforma.
 */
export function CatalogScopeNotice({ canManage }: { canManage: boolean }) {
    if (canManage) {
        return (
            <div className="mb-4 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                <AlertTriangle size={16} className="mt-0.5 shrink-0" />
                <span>
                    O catálogo de modelos de extração é <strong>global</strong>. Alterações em schemas ou layouts afetam{' '}
                    <strong>todos os tenants</strong>.
                </span>
            </div>
        )
    }
    return (
        <div className="mb-4 flex items-start gap-2 rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-600">
            <Lock size={16} className="mt-0.5 shrink-0" />
            <span>
                O catálogo de modelos de extração é global e gerido pelo operador da plataforma. Você tem acesso
                <strong> somente leitura</strong>.
            </span>
        </div>
    )
}
