import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { asApiError } from '../../../shared/utils'
import { activateInvite } from '../services/tenantActivation.service'
import {
    ACTIVATE_ACCOUNT_DEFAULTS,
    activateAccountSchema,
    type ActivateAccountFormValues,
} from '../schemas/activateAccountSchema'

const ERROR_MESSAGES: Record<string, string> = {
    INVITE_NOT_FOUND: 'Convite inválido.',
    INVITE_EXPIRED: 'Este convite expirou. Solicite um novo ao administrador da plataforma.',
    INVITE_ALREADY_USED: 'Este convite já foi utilizado.',
}

export function ActivateAccountForm({ token }: { token: string }) {
    const [error, setError] = useState('')
    const [success, setSuccess] = useState(false)
    const {
        register,
        handleSubmit,
        formState: { isSubmitting, errors },
    } = useForm<ActivateAccountFormValues>({
        resolver: zodResolver(activateAccountSchema),
        defaultValues: ACTIVATE_ACCOUNT_DEFAULTS,
    })

    const onSubmit = handleSubmit(async (values) => {
        setError('')
        try {
            await activateInvite(token, values.password)
            setSuccess(true)
        } catch (err) {
            const apiError = asApiError(err)
            const code = apiError.response?.data?.error?.code
            const detail = apiError.response?.data?.error?.detail
            const detailMessage =
                typeof detail === 'string'
                    ? detail
                    : detail && typeof detail === 'object'
                      ? Object.values(detail).flat().join(' ')
                      : undefined

            setError(detailMessage ?? (code && ERROR_MESSAGES[code]) ?? 'Erro ao ativar a conta.')
        }
    })

    return (
        <div className="flex min-h-screen items-center justify-center bg-zinc-50">
            <div className="w-full max-w-sm rounded-xl border border-zinc-200 bg-white p-8 shadow-sm">
                <div className="mb-6 text-center">
                    <div className="text-2xl font-semibold">DocuParse</div>
                    <div className="mt-1 text-sm text-zinc-500">
                        {success ? 'Conta ativada' : 'Defina sua senha para ativar a conta'}
                    </div>
                </div>

                {success ? (
                    <>
                        <div className="mb-4 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
                            Conta ativada com sucesso! Você já pode entrar com sua senha.
                        </div>
                        <a
                            href="/"
                            className="block w-full rounded-md bg-zinc-900 py-2 text-center text-sm font-medium text-white hover:bg-zinc-700"
                        >
                            Ir para o login
                        </a>
                    </>
                ) : (
                    <>
                        {error && (
                            <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
                        )}
                        <form onSubmit={onSubmit} className="space-y-4">
                            <div>
                                <label
                                    htmlFor="activate-password"
                                    className="mb-1 block text-sm font-medium text-zinc-700"
                                >
                                    Senha
                                </label>
                                <input
                                    id="activate-password"
                                    type="password"
                                    required
                                    minLength={8}
                                    className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                                    placeholder="Mín. 8 caracteres"
                                    {...register('password')}
                                />
                                {errors.password && (
                                    <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
                                )}
                            </div>
                            <div>
                                <label
                                    htmlFor="activate-confirm-password"
                                    className="mb-1 block text-sm font-medium text-zinc-700"
                                >
                                    Confirmar senha
                                </label>
                                <input
                                    id="activate-confirm-password"
                                    type="password"
                                    required
                                    className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                                    placeholder="••••••••"
                                    {...register('confirmPassword')}
                                />
                                {errors.confirmPassword && (
                                    <p className="mt-1 text-xs text-red-600">{errors.confirmPassword.message}</p>
                                )}
                            </div>
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="w-full rounded-md bg-zinc-900 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                            >
                                {isSubmitting ? 'Ativando...' : 'Ativar conta'}
                            </button>
                        </form>
                    </>
                )}
            </div>
        </div>
    )
}
