import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Alert, Field } from '../../../shared/components'
import type { Account } from '../schemas/registry'
import type { Rule } from '../schemas/rules'
import { describeRuleSupplier, leafExpenseAccounts } from '../rules'

const MIN_NAME = 8

const baseSchema = z.object({
    mode: z.enum(['tax', 'name']),
    supplier: z.string().trim(),
    keyword: z.string().trim(),
    ledger_account_id: z.string().min(1, 'Escolha a conta.'),
})

/** Ao editar, o fornecedor já existe e não é pedido: só a conta é validada. */
function buildSchema(editing: boolean) {
    if (editing) return baseSchema
    return baseSchema.superRefine((values, ctx) => {
        if (values.mode === 'tax' && values.supplier.replace(/\D/g, '').length < 11) {
            ctx.addIssue({ code: 'custom', path: ['supplier'], message: 'Informe o CNPJ ou CPF do fornecedor.' })
        }
        if (values.mode === 'name' && values.keyword.length < MIN_NAME) {
            ctx.addIssue({
                code: 'custom',
                path: ['keyword'],
                message: `Informe o nome do fornecedor (mínimo ${MIN_NAME} caracteres).`,
            })
        }
    })
}

export type RuleFormValues = z.infer<typeof baseSchema>

/** Cria uma regra ou, com `rule`, troca a conta dela. Salvar torna a regra manual. */
export function RuleFormDialog({
    rule,
    accounts,
    saving,
    error,
    onSubmit,
    onCancel,
}: {
    rule: Rule | null
    accounts: Account[]
    saving: boolean
    error: string
    onSubmit: (values: RuleFormValues) => void
    onCancel: () => void
}) {
    const {
        register,
        handleSubmit,
        watch,
        formState: { errors },
    } = useForm<RuleFormValues>({
        resolver: zodResolver(buildSchema(rule !== null)),
        defaultValues: { mode: 'tax', supplier: '', keyword: '', ledger_account_id: rule?.ledger_account_id ?? '' },
    })
    const mode = watch('mode')
    const options = leafExpenseAccounts(accounts)

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
            aria-label={rule ? 'Editar regra' : 'Nova regra'}
        >
            <form
                onSubmit={handleSubmit(onSubmit)}
                className="w-full max-w-lg space-y-3 rounded-md border border-zinc-200 bg-white p-4 shadow-lg"
            >
                <div className="text-sm font-semibold text-zinc-900">{rule ? 'Editar regra' : 'Nova regra'}</div>
                {error ? (
                    <Alert tone="error" className="">
                        {error}
                    </Alert>
                ) : null}
                {rule ? (
                    <p className="text-sm text-zinc-700">
                        Fornecedor: <strong>{describeRuleSupplier(rule).title}</strong>
                    </p>
                ) : (
                    <>
                        <fieldset className="flex gap-4 text-sm" aria-label="Como identificar o fornecedor">
                            <label className="flex items-center gap-1">
                                <input type="radio" value="tax" {...register('mode')} /> Por CNPJ ou CPF
                            </label>
                            <label className="flex items-center gap-1">
                                <input type="radio" value="name" {...register('mode')} /> Pelo nome no documento
                            </label>
                        </fieldset>
                        {mode === 'tax' ? (
                            <>
                                <div>
                                    <Field label="CNPJ ou CPF">
                                        <input className="input" inputMode="numeric" {...register('supplier')} />
                                    </Field>
                                    {errors.supplier ? (
                                        <p className="mt-1 text-xs text-red-700">{errors.supplier.message}</p>
                                    ) : null}
                                </div>
                                <Field label="Só se o documento tiver o trecho (opcional)">
                                    <input className="input" {...register('keyword')} />
                                </Field>
                            </>
                        ) : (
                            <div>
                                <Field label="Nome do fornecedor, como aparece no documento">
                                    <input className="input" {...register('keyword')} />
                                </Field>
                                {errors.keyword ? (
                                    <p className="mt-1 text-xs text-red-700">{errors.keyword.message}</p>
                                ) : null}
                            </div>
                        )}
                    </>
                )}
                <div>
                    <Field label="Conta">
                        <select className="input" {...register('ledger_account_id')}>
                            <option value="">Selecione...</option>
                            {options.map((account) => (
                                <option key={account.id} value={account.id}>
                                    {account.code} · {account.name}
                                </option>
                            ))}
                        </select>
                    </Field>
                    {errors.ledger_account_id ? (
                        <p className="mt-1 text-xs text-red-700">{errors.ledger_account_id.message}</p>
                    ) : null}
                </div>
                <p className="text-xs text-zinc-500">
                    A regra vale para todos os condomínios deste plano e passa a ser manual: a atualização do histórico
                    não a altera.
                </p>
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
                        disabled={saving}
                        className="h-9 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                    >
                        {saving ? 'Salvando...' : 'Salvar'}
                    </button>
                </div>
            </form>
        </div>
    )
}
