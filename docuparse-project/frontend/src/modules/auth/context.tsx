import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi, adminApi } from '../../shared/lib/http'
import type { AuthContextValue, User, LoginResponse } from './types'

function decodeJwtTenant(token: string): string | null {
    try {
        const payload = token.split('.')[1]
        const padded = payload + '='.repeat((4 - (payload.length % 4)) % 4)
        return ((JSON.parse(atob(padded)) as Record<string, unknown>).tenant as string | null) ?? null
    } catch {
        return null
    }
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)
    const [currentTenant, setCurrentTenant] = useState<string | null>(() =>
        decodeJwtTenant(localStorage.getItem('access_token') ?? ''),
    )

    useEffect(() => {
        const token = localStorage.getItem('access_token')
        if (!token) {
            setLoading(false)
            return
        }
        authApi
            .get<User>('/me', { headers: { Authorization: `Bearer ${token}` } })
            .then((r) => setUser(r.data))
            .catch(() => {
                localStorage.removeItem('access_token')
                localStorage.removeItem('refresh_token')
            })
            .finally(() => setLoading(false))
    }, [])

    const login = async (email: string, password: string): Promise<void> => {
        const r = await authApi.post<LoginResponse>('/login', { email, password })
        localStorage.setItem('access_token', r.data.access)
        localStorage.setItem('refresh_token', r.data.refresh)
        setUser(r.data.user)
        setCurrentTenant(decodeJwtTenant(r.data.access))
    }

    const logout = async (): Promise<void> => {
        const refresh = localStorage.getItem('refresh_token')
        try {
            if (refresh)
                await authApi.post(
                    '/logout',
                    { refresh },
                    { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } },
                )
        } catch {
            /* ignore */
        }
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setUser(null)
        setCurrentTenant(null)
    }

    const hasPermission = (code: string): boolean => Array.isArray(user?.permissions) && user.permissions.includes(code)

    const switchTenant = async (slug: string): Promise<void> => {
        const r = await adminApi.post<{ data: { access: string; refresh: string } }>(`/tenants/${slug}/switch/`)
        localStorage.setItem('access_token', r.data.data.access)
        localStorage.setItem('refresh_token', r.data.data.refresh)
        setCurrentTenant(decodeJwtTenant(r.data.data.access))
    }

    return (
        <AuthContext.Provider value={{ user, loading, currentTenant, login, logout, hasPermission, switchTenant }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext)
    if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
    return ctx
}
