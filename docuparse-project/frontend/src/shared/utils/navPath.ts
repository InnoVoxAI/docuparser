import type { ActiveView } from '../../types'

/** Caminho de rota (React Router) para um item de navegação — mapeamento 1:1, `id` vira `/id`. */
export function navPath(id: ActiveView): string {
    return `/${id}`
}

/**
 * Visão Geral de Processos com o drawer de validação aberto para um documento. É o contrato
 * entre as telas que querem levar o analista à validação (Pagamentos, por exemplo) e a Visão
 * Geral, que lê o parâmetro `validar`. Passando `state: { from }`, fechar o drawer volta à tela
 * de origem.
 */
export const VALIDATION_DRAWER_PARAM = 'validar'

export function validationDrawerPath(documentId: string): string {
    return `/?${VALIDATION_DRAWER_PARAM}=${encodeURIComponent(documentId)}`
}
