import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { adminApi } from '../../../shared/lib/http'
import { asApiError } from '../../../shared/utils'
import { useAuth } from '../../auth'
import type { Tenant } from '../../../types'
import { TenantCreateForm } from './TenantCreateForm'
import { TenantsTable } from './TenantsTable'

export function TenantsView() {
    const { currentTenant, switchTenant } = useAuth()
    const [tenants, setTenants] = useState<Tenant[]>([])
    const [loadingList, setLoadingList] = useState(true)
    const [listError, setListError] = useState('')
    const [formSlug, setFormSlug] = useState('')
    const [formName, setFormName] = useState('')
    const [formAdminName, setFormAdminName] = useState('')
    const [formAdminEmail, setFormAdminEmail] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [formError, setFormError] = useState('')
    const [toggleError, setToggleError] = useState<Record<string, string>>({})
    const [expandedSlug, setExpandedSlug] = useState<string | null>(null)
    const [switchingSlug, setSwitchingSlug] = useState<string | null>(null)
    const [switchError, setSwitchError] = useState<Record<string, string>>({})

    const fetchTenants = useCallback(async () => {
        setLoadingList(true)
        setListError('')
        try {
            const r = await adminApi.get<{ data: Tenant[] }>('/tenants/')
            setTenants(r.data.data)
        } catch {
            setListError('Falha ao carregar tenants.')
        } finally {
            setLoadingList(false)
        }
    }, [])

    useEffect(() => {
        fetchTenants()
    }, [fetchTenants])

    const handleCreate = async (e: FormEvent) => {
        e.preventDefault()
        setSubmitting(true)
        setFormError('')
        try {
            await adminApi.post('/tenants/', {
                slug: formSlug,
                name: formName,
                admin_name: formAdminName,
                admin_email: formAdminEmail,
            })
            setFormSlug('')
            setFormName('')
            setFormAdminName('')
            setFormAdminEmail('')
            await fetchTenants()
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

            if (code === 'ADMIN_EMAIL_IN_USE') {
                setFormError(detailMessage ?? `Email "${formAdminEmail}" já está em uso.`)
            } else if (code === 'TENANT_EXISTS' || apiError.response?.status === 409) {
                setFormError(detailMessage ?? `Tenant com slug "${formSlug}" já existe.`)
            } else if (code === 'VALIDATION_ERROR') {
                setFormError(detailMessage ?? 'Dados inválidos.')
            } else {
                setFormError(detailMessage ?? 'Erro ao criar tenant.')
            }
        } finally {
            setSubmitting(false)
        }
    }

    const handleToggle = async (slug: string, currentActive: boolean) => {
        setToggleError((prev) => ({ ...prev, [slug]: '' }))
        try {
            await adminApi.patch(`/tenants/${slug}/`, { is_active: !currentActive })
            await fetchTenants()
        } catch (err) {
            const apiError = asApiError(err)
            const detail = apiError.response?.data?.error?.detail
            setToggleError((prev) => ({
                ...prev,
                [slug]:
                    apiError.response?.status === 409
                        ? (detail ?? 'Não é possível desativar o único tenant ativo.')
                        : (detail ?? 'Erro ao atualizar tenant.'),
            }))
        }
    }

    const handleSwitch = async (slug: string) => {
        setSwitchError((prev) => ({ ...prev, [slug]: '' }))
        setSwitchingSlug(slug)
        try {
            await switchTenant(slug)
        } catch (err) {
            const detail = asApiError(err).response?.data?.error?.detail
            setSwitchError((prev) => ({ ...prev, [slug]: detail ?? 'Erro ao alternar tenant.' }))
        } finally {
            setSwitchingSlug(null)
        }
    }

    return (
        <div className="space-y-6">
            <TenantCreateForm
                slug={formSlug}
                name={formName}
                adminName={formAdminName}
                adminEmail={formAdminEmail}
                submitting={submitting}
                error={formError}
                onSlugChange={setFormSlug}
                onNameChange={setFormName}
                onAdminNameChange={setFormAdminName}
                onAdminEmailChange={setFormAdminEmail}
                onSubmit={handleCreate}
            />

            {listError ? <p className="text-sm text-red-600">{listError}</p> : null}
            {loadingList ? <p className="text-sm text-zinc-500">Carregando...</p> : null}

            {!loadingList && tenants.length > 0 ? (
                <TenantsTable
                    tenants={tenants}
                    currentTenant={currentTenant}
                    expandedSlug={expandedSlug}
                    switchingSlug={switchingSlug}
                    switchError={switchError}
                    toggleError={toggleError}
                    onToggleExpand={(slug) => setExpandedSlug((prev) => (prev === slug ? null : slug))}
                    onSwitch={handleSwitch}
                    onToggle={handleToggle}
                />
            ) : null}
        </div>
    )
}
