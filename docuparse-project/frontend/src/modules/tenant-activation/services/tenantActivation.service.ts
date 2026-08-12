import { adminApi } from '../../../shared/lib/http'
import type { ActivateInviteResult } from '../types'

export async function activateInvite(token: string, password: string): Promise<ActivateInviteResult> {
    const response = await adminApi.post<{ data: ActivateInviteResult }>(
        `/tenants/invites/${encodeURIComponent(token)}/activate/`,
        { password },
    )
    return response.data.data
}
