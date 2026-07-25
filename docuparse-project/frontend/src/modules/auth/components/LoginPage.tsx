import { useState } from 'react'
import { LoginForm } from './LoginForm'
import { RegisterForm } from './RegisterForm'

export function LoginPage() {
    const [mode, setMode] = useState<'login' | 'register'>(() => {
        const params = new URLSearchParams(window.location.search)
        return params.has('tenant') ? 'register' : 'login'
    })
    const [success, setSuccess] = useState('')

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

                {mode === 'login' ? (
                    <LoginForm onSwitchToRegister={() => setMode('register')} />
                ) : (
                    <RegisterForm
                        onSwitchToLogin={() => setMode('login')}
                        onRegistered={(message) => {
                            setSuccess(message)
                            setMode('login')
                        }}
                    />
                )}
            </div>
        </div>
    )
}
