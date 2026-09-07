import type { LayoutConfig, SchemaConfig } from '../../../types'
import { useAuth } from '../../auth'
import { CatalogScopeNotice } from './CatalogScopeNotice'
import { ConfigList } from './ConfigList'
import { ExtractionBuilder } from './ExtractionBuilder'
import { SchemaList } from './SchemaList'

/**
 * Container da área "Extração". O catálogo de schemas/layouts é global
 * (spec 018): sem a permissão de plataforma `tenants.manage` o builder
 * LangExtract fica indisponível e a área mostra apenas a listagem do
 * catálogo em modo leitura.
 */
export function ExtractionPanel({ schemas, layouts }: { schemas: SchemaConfig[]; layouts: LayoutConfig[] }) {
    const { hasPermission } = useAuth()

    if (!hasPermission('tenants.manage')) {
        return (
            <div className="p-4">
                <CatalogScopeNotice canManage={false} />
                <div className="grid gap-4 lg:grid-cols-2">
                    <SchemaList schemas={schemas} readOnly />
                    <ConfigList
                        title="Layouts existentes"
                        items={layouts}
                        primaryKey="layout"
                        secondaryKey="document_type"
                    />
                </div>
            </div>
        )
    }

    return <ExtractionBuilder schemas={schemas} layouts={layouts} />
}
