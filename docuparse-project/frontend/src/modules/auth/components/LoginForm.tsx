import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { asApiError } from '../../../shared/utils'
import { useAuth } from '../context'
import { LOGIN_DEFAULTS, loginSchema, type LoginFormValues } from '../schemas/loginSchema'

export function LoginForm({ onSwitchToRegister }: { onSwitchToRegister: () => void }) {
    const { login } = useAuth()
    const [error, setError] = useState('')
    const {
        register,
        handleSubmit,
        formState: { isSubmitting },
    } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema), defaultValues: LOGIN_DEFAULTS })

    const onSubmit = handleSubmit(async (values) => {
        setError('')
        try {
            await login(values.email, values.password)
        } catch (err) {
            const e = asApiError(err)
            const detail = e.response?.data?.detail
            setError(
                e.response?.status === 403
                    ? detail || 'Conta inativa. Aguarde ativação pelo administrador.'
                    : detail || 'Credenciais inválidas.',
            )
        }
    })

    return (
        <>
            {error && <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
            <form onSubmit={onSubmit} className="space-y-4">
                <div>
                    <label htmlFor="login-email" className="mb-1 block text-sm font-medium text-zinc-700">
                        E-mail
                    </label>
                    <input
                        id="login-email"
                        type="email"
                        required
                        className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                        placeholder="voce@empresa.com"
                        {...register('email')}
                    />
                </div>
                <div>
                    <label htmlFor="login-password" className="mb-1 block text-sm font-medium text-zinc-700">
                        Senha
                    </label>
                    <input
                        id="login-password"
                        type="password"
                        required
                        className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                        placeholder="••••••••"
                        {...register('password')}
                    />
                </div>
                <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full rounded-md bg-zinc-900 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                >
                    {isSubmitting ? 'Entrando...' : 'Entrar'}
                </button>
                <button
                    type="button"
                    onClick={onSwitchToRegister}
                    className="w-full text-center text-sm text-zinc-500 hover:text-zinc-800"
                >
                    Criar conta
                </button>
            </form>
        </>
    )
}
