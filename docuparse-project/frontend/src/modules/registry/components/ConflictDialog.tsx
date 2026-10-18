import type { ReactNode } from 'react'
import { useForm, type UseFormRegisterReturn } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Alert } from '../../../shared/components'
import type { Condominium, Proposal } from '../schemas/registry'
import { formatCnpj } from '../utils'

const NONE = '__none__'

const formSchema = z.object({ choice: z.string().min(1, 'Escolha uma opção.') })
type FormValues = z.infer<typeof formSchema>

interface Candidate {
    external_id: string
    name: string
    address: string
}

function candidatesOf(proposal: Proposal): Candidate[] {
    const raw = proposal.data.cnpj_candidates
    return Array.isArray(raw) ? (raw as Candidate[]) : []
}

function Option({
    value,
    label,
    field,
    children,
}: {
    value: string
    label: string
    field: UseFormRegisterReturn
    children?: ReactNode
}) {
    return (
        <label className="flex cursor-pointer items-start gap-2 rounded-md border border-zinc-200 p-3 text-sm has-[:checked]:border-zinc-900">
            <input type="radio" value={value} className="mt-1" aria-label={label} {...field} />
            <span>
                <span className="block font-medium text-zinc-900">{label}</span>
                {children}
            </span>
        </label>
    )
}

/** Resolve um conflito de CNPJ: registros lado a lado e a escolha do analista. */
export function ConflictDialog({
    proposal,
    local,
    busy,
    error,
    onSubmit,
    onCancel,
}: {
    proposal: Proposal
    /** Cadastro local que já usa o CNPJ (só no conflito com cadastro local). */
    local: Condominium | undefined
    busy: boolean
    error: string
    onSubmit: (resolution: Record<string, unknown>) => void
    onCancel: () => void
}) {
    const duplicated = proposal.data.conflict_kind === 'cnpj_duplicated'
    const cnpj = String(duplicated ? (proposal.data.source_cnpj ?? '') : (proposal.data.cnpj ?? ''))
    const { register, handleSubmit, formState } = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: { choice: '' },
    })

    const choiceField = register('choice')
    const submit = handleSubmit(({ choice }) => {
        onSubmit(duplicated ? { cnpj_owner: choice === NONE ? null : choice } : { link_to_local: choice === 'link' })
    })

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
            aria-label="Resolver conflito de CNPJ"
        >
            <form
                onSubmit={submit}
                className="max-h-full w-full max-w-2xl space-y-3 overflow-y-auto rounded-md border border-zinc-200 bg-white p-4 shadow-lg"
            >
                <div className="text-sm font-semibold text-zinc-900">Conflito de CNPJ {formatCnpj(cnpj)}</div>
                <p className="text-sm text-zinc-600">
                    {duplicated
                        ? 'Mais de um cadastro do Superlógica usa este CNPJ, com nomes ou endereços diferentes. Escolha qual fica com o CNPJ; os demais entram sem CNPJ.'
                        : 'Já existe um cadastro local com este CNPJ. Informe se é o mesmo condomínio.'}
                </p>
                {error ? <Alert tone="error">{error}</Alert> : null}
                <fieldset className="grid gap-2 sm:grid-cols-2" aria-label="Opções">
                    {duplicated ? (
                        <>
                            {candidatesOf(proposal).map((candidate) => (
                                <Option
                                    key={candidate.external_id}
                                    value={candidate.external_id}
                                    label={`CNPJ fica com ${candidate.name}`}
                                    field={choiceField}
                                >
                                    <span className="block text-xs text-zinc-500">
                                        {candidate.address || 'Sem endereço'}
                                    </span>
                                    <span className="block text-xs text-zinc-500">
                                        Superlógica #{candidate.external_id}
                                    </span>
                                </Option>
                            ))}
                            <Option value={NONE} label="Nenhum fica com o CNPJ" field={choiceField} />
                        </>
                    ) : (
                        <>
                            <Option value="link" label="É o mesmo condomínio" field={choiceField}>
                                <span className="block text-xs text-zinc-500">
                                    Liga o cadastro local ({local?.name ?? 'cadastro local'}) a este do Superlógica.
                                </span>
                            </Option>
                            <Option value="other" label="É outro condomínio" field={choiceField}>
                                <span className="block text-xs text-zinc-500">
                                    Importa {String(proposal.data.name)} sem CNPJ.
                                </span>
                            </Option>
                        </>
                    )}
                </fieldset>
                {formState.errors.choice ? (
                    <p className="text-xs text-red-700">{formState.errors.choice.message}</p>
                ) : null}
                <div className="flex justify-end gap-2">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="h-9 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        Cancelar
                    </button>
                    <button
                        type="submit"
                        disabled={busy}
                        className="h-9 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                    >
                        {busy ? 'Resolvendo...' : 'Resolver'}
                    </button>
                </div>
            </form>
        </div>
    )
}
