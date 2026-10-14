import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Alert } from '../../../shared/components'

const pickerSchema = z.object({ value: z.string().min(1, 'Selecione uma opção.') })
type PickerValues = z.infer<typeof pickerSchema>

export interface PickerOption {
    value: string
    label: string
}

/** Uma lista + botão de salvar. Usado para escolher o condomínio e a conta do documento. */
export function OptionPickerForm({
    label,
    options,
    defaultValue,
    submitLabel,
    loading = false,
    saving,
    error,
    onSubmit,
    onCancel,
}: {
    label: string
    options: PickerOption[]
    defaultValue: string
    submitLabel: string
    /** Lista de opções ainda carregando: seletor desabilitado. */
    loading?: boolean
    saving: boolean
    error: string
    onSubmit: (value: string) => Promise<unknown>
    onCancel?: () => void
}) {
    const {
        register,
        handleSubmit,
        watch,
        formState: { errors },
    } = useForm<PickerValues>({ resolver: zodResolver(pickerSchema), defaultValues: { value: defaultValue } })
    const unchanged = watch('value') === defaultValue

    // O erro da API aparece no `Alert`; falha de rede/validação não deve virar rejeição não tratada.
    const submit = handleSubmit(async ({ value }) => {
        try {
            await onSubmit(value)
        } catch {
            /* exibido via `error` */
        }
    })

    return (
        <form onSubmit={submit} className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
                <select
                    aria-label={label}
                    className="input min-w-0 flex-1"
                    disabled={saving || loading}
                    {...register('value')}
                >
                    <option value="">{loading ? 'Carregando...' : 'Selecione...'}</option>
                    {options.map((option) => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
                <button
                    type="submit"
                    disabled={saving || unchanged}
                    className="inline-flex h-9 items-center rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                >
                    {saving ? 'Salvando...' : submitLabel}
                </button>
                {onCancel ? (
                    <button
                        type="button"
                        onClick={onCancel}
                        className="inline-flex h-9 items-center rounded-md border border-zinc-300 px-3 text-sm hover:bg-zinc-50"
                    >
                        Cancelar
                    </button>
                ) : null}
            </div>
            {errors.value ? <p className="text-xs text-red-700">{errors.value.message}</p> : null}
            {error ? <Alert tone="error">{error}</Alert> : null}
        </form>
    )
}
