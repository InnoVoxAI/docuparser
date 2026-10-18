import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Alert, Field } from '../../../shared/components'
import { useCreateCondominium } from '../hooks'
import type { Chart } from '../schemas/registry'
import { readFieldError } from '../utils'

const formSchema = z.object({
    name: z.string().trim().min(1, 'Informe o nome do condomínio.'),
    cnpj: z
        .string()
        .trim()
        .refine((value) => value === '' || value.replace(/\D/g, '').length === 14, 'O CNPJ precisa ter 14 dígitos.'),
    chart_of_accounts_id: z.string(),
})

type FormValues = z.infer<typeof formSchema>

export function CreateCondominiumDialog({ charts, onClose }: { charts: Chart[]; onClose: () => void }) {
    const create = useCreateCondominium()
    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: { name: '', cnpj: '', chart_of_accounts_id: '' },
    })

    const onSubmit = handleSubmit((values) => {
        create.mutate(
            {
                name: values.name,
                cnpj: values.cnpj,
                chart_of_accounts_id: values.chart_of_accounts_id || null,
            },
            { onSuccess: onClose },
        )
    })

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
            aria-label="Novo condomínio"
        >
            <form
                onSubmit={onSubmit}
                className="w-full max-w-md space-y-3 rounded-md border border-zinc-200 bg-white p-4 shadow-lg"
            >
                <div className="text-sm font-semibold text-zinc-900">Novo condomínio</div>
                {create.error ? (
                    <Alert tone="error">
                        {readFieldError(create.error, 'Nao foi possivel cadastrar o condominio.')}
                    </Alert>
                ) : null}
                <div>
                    <Field label="Nome">
                        <input className="input" {...register('name')} />
                    </Field>
                    {errors.name ? <p className="mt-1 text-xs text-red-700">{errors.name.message}</p> : null}
                </div>
                <div>
                    <Field label="CNPJ (opcional)">
                        <input className="input" inputMode="numeric" {...register('cnpj')} />
                    </Field>
                    {errors.cnpj ? <p className="mt-1 text-xs text-red-700">{errors.cnpj.message}</p> : null}
                </div>
                <Field label="Plano de contas">
                    <select className="input" {...register('chart_of_accounts_id')}>
                        <option value="">Sem plano por enquanto</option>
                        {charts
                            .filter((chart) => chart.is_active)
                            .map((chart) => (
                                <option key={chart.id} value={chart.id}>
                                    {chart.name}
                                </option>
                            ))}
                    </select>
                </Field>
                <div className="flex justify-end gap-2">
                    <button
                        type="button"
                        onClick={onClose}
                        className="h-9 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        Cancelar
                    </button>
                    <button
                        type="submit"
                        disabled={create.isPending}
                        className="h-9 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                    >
                        {create.isPending ? 'Salvando...' : 'Cadastrar'}
                    </button>
                </div>
            </form>
        </div>
    )
}
