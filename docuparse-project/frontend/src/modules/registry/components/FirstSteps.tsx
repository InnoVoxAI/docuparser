import { Link } from 'react-router'
import { navPath } from '../../../shared/utils'

/** Guia da primeira vez: some assim que existe algum condomínio ou plano. */
export function FirstSteps({ credentialsConfigured }: { credentialsConfigured: boolean | undefined }) {
    return (
        <section aria-label="Primeiros passos" className="rounded-md border border-zinc-200 bg-white p-4 text-sm">
            <div className="mb-2 font-semibold text-zinc-900">Primeiros passos</div>
            <ol className="list-decimal space-y-1 pl-5 text-zinc-700">
                <li>
                    {credentialsConfigured ? (
                        'Credenciais do Superlógica configuradas.'
                    ) : (
                        <>
                            Informe as credenciais do Superlógica em{' '}
                            <Link to={navPath('integrations')} className="font-medium underline">
                                Integrações
                            </Link>
                            .
                        </>
                    )}
                </li>
                <li>Clique em "Sincronizar com Superlógica". Leva alguns segundos.</li>
                <li>Confirme os planos de contas e depois os condomínios. Nada entra sem a sua confirmação.</li>
            </ol>
            <p className="mt-2 text-xs text-zinc-500">
                Para cadastrar um único condomínio à mão, use "Novo condomínio".
            </p>
        </section>
    )
}
