import { Link } from 'react-router'
import { CheckCircle2 } from 'lucide-react'
import { EmptyState } from '../../../shared/components'
import { navPath } from '../../../shared/utils'
import type { EntityType } from '../schemas/registry'
import { ENTITY_LABELS } from '../utils'

/** Aba vazia: diz o que fazer em seguida (outra aba com pendências, ou ver o resultado em Cadastros). */
export function ReviewEmpty({
    allDone,
    nextTab,
    nextCount,
    onGoToNext,
}: {
    allDone: boolean
    nextTab: EntityType | undefined
    nextCount: number
    onGoToNext: () => void
}) {
    return (
        <div className="rounded-md border border-zinc-200 bg-white">
            <EmptyState icon={CheckCircle2} text="Nada pendente de confirmação nesta aba." />
            <div className="flex flex-col items-center gap-2 pb-6 text-sm">
                {allDone ? (
                    <>
                        <p className="font-medium text-emerald-800">Tudo confirmado.</p>
                        <Link
                            to={navPath('registry')}
                            className="rounded-md bg-zinc-900 px-3 py-2 font-medium text-white hover:bg-zinc-700"
                        >
                            Ver o resultado em Cadastros
                        </Link>
                    </>
                ) : nextTab ? (
                    <button
                        type="button"
                        onClick={onGoToNext}
                        className="rounded-md border border-zinc-300 px-3 py-2 font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        Ir para {ENTITY_LABELS[nextTab]} ({nextCount})
                    </button>
                ) : null}
            </div>
        </div>
    )
}
