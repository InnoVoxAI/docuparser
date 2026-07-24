import { useNavigate, useOutletContext } from 'react-router'
import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { navPath, type AppOutletContext } from '../../../main'
import { ValidationView } from '../components/ValidationView'

export function ValidationRoute() {
    const { schemas, selectedDocument, selectedDocumentId, refreshData } = useOutletContext<AppOutletContext>()
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
