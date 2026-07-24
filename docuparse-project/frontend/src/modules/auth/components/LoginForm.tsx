import type { FormEvent } from 'react'

export function LoginForm({
    email,
    password,
    submitting,
    onEmailChange,
    onPasswordChange,
    onSubmit,
    onSwitchToRegister,
}: {
    email: string
    password: string
    submitting: boolean
    onEmailChange: (value: string) => void
    onPasswordChange: (value: string) => void
    onSubmit: (e: FormEvent) => void
    onSwitchToRegister: () => void
}) {
    return (
        <form onSubmit={onSubmit} className="space-y-4">
            <div>
                <label htmlFor="login-email" className="mb-1 block text-sm font-medium text-zinc-700">
                    E-mail
                </label>
                <input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(e) => onEmailChange(e.target.value)}
                    required
                    className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                    placeholder="voce@empresa.com"
                />
            </div>
            <div>
                <label htmlFor="login-password" className="mb-1 block text-sm font-medium text-zinc-700">
                    Senha
                </label>
                <input
                    id="login-password"
                    type="password"
                    value={password}
                    onChange={(e) => onPasswordChange(e.target.value)}
                    required
                    className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                    placeholder="••••••••"
                />
            </div>
            <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-md bg-zinc-900 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
            >
                {submitting ? 'Entrando...' : 'Entrar'}
            </button>
            <button
                type="button"
                onClick={onSwitchToRegister}
                className="w-full text-center text-sm text-zinc-500 hover:text-zinc-800"
            >
                Criar conta
            </button>
        </form>
    )
}
