import { Link, useInRouterContext } from 'react-router'
import { navPath } from '../../../shared/utils'

/** Depois de salvar as credenciais, o próximo passo é sincronizar em Cadastros. */
export function NextStepHint() {
    const inRouter = useInRouterContext()
    return (
        <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            Credenciais do Superlógica configuradas.{' '}
            {inRouter ? (
                <Link to={navPath('registry')} className="font-medium underline">
                    Ir para Cadastros e sincronizar
                </Link>
            ) : null}
        </p>
    )
}
