import { useNavigate, useOutletContext } from 'react-router'
import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { useSchemasQuery } from '../../settings'
import { navPath, type AppOutletContext } from '../../../main'
import { ValidationView } from '../components/ValidationView'

/**
 * `schemas` vem de `useSchemasQuery` (barrel de `modules/settings`) em vez de
 * `AppOutletContext` — dependência cruzada legítima documentada em
 * `contracts/module-boundaries.md` ("settings ... Consumido por:
 * modules/documents"), necessária desde que `schemas`/`layouts` saíram do
 * outlet context (Fase 4f/T036-T040, decisão #5).
 */
export function ValidationRoute() {
    const { selectedDocument, selectedDocumentId, refreshData } = useOutletContext<AppOutletContext>()
    const { data: schemas } = useSchemasQuery()
    const navigate = useNavigate()
    return (
        <PermissionGuard code="documents.validate" fallback={<AcessoNaoAutorizado />}>
            <ValidationView
                schemas={schemas}
                selectedDocument={selectedDocument}
                selectedDocumentId={selectedDocumentId}
                onValidated={refreshData}
                onBackToInbox={() => navigate(navPath('inbox'))}
            />
        </PermissionGuard>
    )
}
