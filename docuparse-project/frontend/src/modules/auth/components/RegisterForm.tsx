import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { authApi } from '../../../shared/lib/http'
import { asApiError } from '../../../shared/utils'
import { getRegisterDefaults, registerSchema, type RegisterFormValues } from '../schemas/registerSchema'

export function RegisterForm({
    onSwitchToLogin,
    onRegistered,
}: {
    onSwitchToLogin: () => void
    onRegistered: (message: string) => void
}) {
    const [error, setError] = useState('')
    const {
        register,
        handleSubmit,
        formState: { isSubmitting },
    } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema), defaultValues: getRegisterDefaults() })

    const onSubmit = handleSubmit(
        async (values) => {
            setError('')
            try {
                await authApi.post('/register', {
                    name: values.name,
                    email: values.email,
                    password: values.password,
                    tenant_slug: values.tenantSlug,
                })
                onRegistered('Conta criada! Aguarde a ativação pelo administrador.')
            } catch (err) {
                const data = asApiError(err).response?.data
                setError(data?.detail || data?.email?.[0] || data?.password?.[0] || 'Erro ao criar conta.')
            }
        },
        // Espelha o `if (password !== confirmPassword)` original: com HTML5 `required`/`pattern`/
        // `minLength` já bloqueando os demais campos antes de chegar aqui, o único erro de validação
        // que realisticamente cai neste callback é o `.refine` de confirmação de senha (T044).
        (formErrors) => {
            const firstMessage = Object.values(formErrors)[0]?.message
            if (firstMessage) setError(firstMessage)
        },
    )

    return (
        <>
            {error && <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
            <form onSubmit={onSubmit} className="space-y-4">
                <div>
                    <label htmlFor="register-name" className="mb-1 block text-sm font-medium text-zinc-700">
                        Nome
                    </label>
                    <input
                        id="register-name"
                        type="text"
                        required
                        className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                        placeholder="Seu nome"
                        {...register('name')}
                    />
                </div>
                <div>
                    <label htmlFor="register-tenant-slug" className="mb-1 block text-sm font-medium text-zinc-700">
                        Código do tenant
                    </label>
                    <input
                        id="register-tenant-slug"
                        type="text"
                        required
                        pattern="[a-z0-9-]+"
                        title="Apenas letras minúsculas, números e hífens"
                        className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none font-mono"
                        placeholder="ex: acme"
                        {...register('tenantSlug')}
                    />
                    <p className="mt-1 text-xs text-zinc-400">Solicite o código ao administrador do sistema.</p>
                </div>
                <div>
                    <label htmlFor="register-email" className="mb-1 block text-sm font-medium text-zinc-700">
                        E-mail
                    </label>
                    <input
                        id="register-email"
                        type="email"
                        required
                        className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                        placeholder="voce@empresa.com"
                        {...register('email')}
                    />
                </div>
                <div>
                    <label htmlFor="register-password" className="mb-1 block text-sm font-medium text-zinc-700">
                        Senha
                    </label>
                    <input
                        id="register-password"
                        type="password"
                        required
                        minLength={8}
                        className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                        placeholder="Mín. 8 caracteres"
                        {...register('password')}
                    />
                </div>
                <div>
                    <label htmlFor="register-confirm-password" className="mb-1 block text-sm font-medium text-zinc-700">
                        Confirmar senha
                    </label>
                    <input
                        id="register-confirm-password"
                        type="password"
                        required
                        className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                        placeholder="••••••••"
                        {...register('confirmPassword')}
                    />
                </div>
                <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full rounded-md bg-zinc-900 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                >
                    {isSubmitting ? 'Criando conta...' : 'Criar conta'}
                </button>
                <button
                    type="button"
                    onClick={onSwitchToLogin}
                    className="w-full text-center text-sm text-zinc-500 hover:text-zinc-800"
                >
                    Já tenho conta
                </button>
            </form>
        </>
    )
}
