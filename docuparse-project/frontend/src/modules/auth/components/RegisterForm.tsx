import type { FormEvent } from 'react'

export function RegisterForm({
    name,
    tenantSlug,
    email,
    password,
    confirmPassword,
    submitting,
    onNameChange,
    onTenantSlugChange,
    onEmailChange,
    onPasswordChange,
    onConfirmPasswordChange,
    onSubmit,
    onSwitchToLogin,
}: {
    name: string
    tenantSlug: string
    email: string
    password: string
    confirmPassword: string
    submitting: boolean
    onNameChange: (value: string) => void
    onTenantSlugChange: (value: string) => void
    onEmailChange: (value: string) => void
    onPasswordChange: (value: string) => void
    onConfirmPasswordChange: (value: string) => void
    onSubmit: (e: FormEvent) => void
    onSwitchToLogin: () => void
}) {
    return (
        <form onSubmit={onSubmit} className="space-y-4">
            <div>
                <label htmlFor="register-name" className="mb-1 block text-sm font-medium text-zinc-700">
                    Nome
                </label>
                <input
                    id="register-name"
                    type="text"
                    value={name}
                    onChange={(e) => onNameChange(e.target.value)}
                    required
                    className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                    placeholder="Seu nome"
                />
            </div>
            <div>
                <label htmlFor="register-tenant-slug" className="mb-1 block text-sm font-medium text-zinc-700">
                    Código do tenant
                </label>
                <input
                    id="register-tenant-slug"
                    type="text"
                    value={tenantSlug}
                    onChange={(e) => onTenantSlugChange(e.target.value)}
                    required
                    pattern="[a-z0-9-]+"
                    title="Apenas letras minúsculas, números e hífens"
                    className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none font-mono"
                    placeholder="ex: acme"
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
                    value={email}
                    onChange={(e) => onEmailChange(e.target.value)}
                    required
                    className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                    placeholder="voce@empresa.com"
                />
            </div>
            <div>
                <label htmlFor="register-password" className="mb-1 block text-sm font-medium text-zinc-700">
                    Senha
                </label>
                <input
                    id="register-password"
                    type="password"
                    value={password}
                    onChange={(e) => onPasswordChange(e.target.value)}
                    required
                    minLength={8}
                    className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
                    placeholder="Mín. 8 caracteres"
                />
            </div>
            <div>
                <label htmlFor="register-confirm-password" className="mb-1 block text-sm font-medium text-zinc-700">
                    Confirmar senha
                </label>
                <input
                    id="register-confirm-password"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => onConfirmPasswordChange(e.target.value)}
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
                {submitting ? 'Criando conta...' : 'Criar conta'}
            </button>
            <button
                type="button"
                onClick={onSwitchToLogin}
                className="w-full text-center text-sm text-zinc-500 hover:text-zinc-800"
            >
                Já tenho conta
            </button>
        </form>
    )
}
