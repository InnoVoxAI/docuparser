export interface AdminRoleRef {
    id: string
    name: string
}

export interface AdminUser {
    id: string
    name: string
    email: string
    role?: AdminRoleRef | null
    is_active?: boolean
    [key: string]: unknown
}

export interface AdminPermission {
    code: string
    name?: string
    description?: string
    [key: string]: unknown
}

export interface AdminRole {
    id: string
    name: string
    permissions?: Array<AdminPermission | string>
    users_count?: number
    [key: string]: unknown
}
