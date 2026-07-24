import { useState, type FormEvent } from 'react'
import { authApi } from '../../../shared/lib/http'
import { asApiError } from '../../../shared/utils'
import { useAuth } from '../context'
import { LoginForm } from './LoginForm'
import { RegisterForm } from './RegisterForm'

export function LoginPage() {
    const { login } = useAuth()
    const [mode, setMode] = useState<'login' | 'register'>(() => {
        const params = new URLSearchParams(window.location.search)
        return params.has('tenant') ? 'register' : 'login'
    })
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [name, setName] = useState('')
    const [tenantSlug, setTenantSlug] = useState(() => {
        const params = new URLSearchParams(window.location.search)
        return params.get('tenant') ?? ''
    })
    const [confirmPassword, setConfirmPassword] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')

    const handleLogin = async (e: FormEvent) => {
        e.preventDefault()
        setError('')
        setSubmitting(true)
        try {
            await login(email, password)
        } catch (err) {
            const e = asApiError(err)
            const detail = e.response?.data?.detail
            setError(
                e.response?.status === 403
                    ? detail || 'Conta inativa. Aguarde ativação pelo administrador.'
                    : detail || 'Credenciais inválidas.',
            )
        } finally {
            setSubmitting(false)
        }
    }

    const handleRegister = async (e: FormEvent) => {
        e.preventDefault()
        setError('')
        if (password !== confirmPassword) {
            setError('As senhas não coincidem.')
            return
        }
        setSubmitting(true)
        try {
            await authApi.post('/register', { name, email, password, tenant_slug: tenantSlug })
            setSuccess('Conta criada! Aguarde a ativação pelo administrador.')
            setMode('login')
            setEmail('')
            setPassword('')
        } catch (err) {
            const data = asApiError(err).response?.data
            setError(data?.detail || data?.email?.[0] || data?.password?.[0] || 'Erro ao criar conta.')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-zinc-50">
            <div className="w-full max-w-sm rounded-xl border border-zinc-200 bg-white p-8 shadow-sm">
                <div className="mb-6 text-center">
                    <div className="text-2xl font-semibold">DocuParse</div>
                    <div className="mt-1 text-sm text-zinc-500">
                        {mode === 'login' ? 'Entre com sua conta para continuar' : 'Criar nova conta'}
                    </div>
                </div>
                {success && (
                    <div className="mb-4 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">{success}</div>
                )}
                {error && <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

                {mode === 'login' ? (
                    <LoginForm
                        email={email}
                        password={password}
                        submitting={submitting}
                        onEmailChange={setEmail}
                        onPasswordChange={setPassword}
                        onSubmit={handleLogin}
                        onSwitchToRegister={() => {
                            setMode('register')
                            setError('')
                        }}
                    />
                ) : (
                    <RegisterForm
                        name={name}
                        tenantSlug={tenantSlug}
                        email={email}
                        password={password}
                        confirmPassword={confirmPassword}
                        submitting={submitting}
                        onNameChange={setName}
                        onTenantSlugChange={setTenantSlug}
                        onEmailChange={setEmail}
                        onPasswordChange={setPassword}
                        onConfirmPasswordChange={setConfirmPassword}
                        onSubmit={handleRegister}
                        onSwitchToLogin={() => {
                            setMode('login')
                            setError('')
                        }}
                    />
                )}
            </div>
        </div>
    )
}
