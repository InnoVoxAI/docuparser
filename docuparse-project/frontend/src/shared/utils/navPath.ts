import type { ActiveView } from '../../types'

/** Caminho de rota (React Router) para um item de navegação — mapeamento 1:1, `id` vira `/id`. */
export function navPath(id: ActiveView): string {
    return `/${id}`
}
