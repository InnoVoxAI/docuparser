import { useNavigate } from 'react-router'
import { validationDrawerPath } from '../../../shared/utils'

/** De onde o analista veio: a Visão Geral usa isto para voltar ao fechar o drawer. */
export const PAYMENTS_PATH = '/payments'

/**
 * Leva o analista à validação de um documento: a Visão Geral de Processos com o drawer
 * aberto (a tela nova). Fechar o drawer volta para Pagamentos.
 */
export function useOpenValidation(): (documentId: string) => void {
    const navigate = useNavigate()
    return (documentId) => navigate(validationDrawerPath(documentId), { state: { from: PAYMENTS_PATH } })
}
