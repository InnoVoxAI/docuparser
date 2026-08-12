export interface AdminRoleRef {
    id: string
    name: string
    is_platform_role?: boolean
}

// Usuários/roles/permissões vêm de serializers RBAC de schema fixo (não de um
// payload de worker/documento variável) — os índices permissivos aqui não
// tinham nenhum consumidor de chave dinâmica (verificado: UserTable/
// RoleTable/RoleFormModal/GerenciarUsuarios/GerenciarRoles só leem os campos
// nomeados abaixo), então foram removidos (T054).
export interface AdminUser {
    id: string
    name: string
    email: string
    role?: AdminRoleRef | null
    is_active?: boolean
    invite_pending?: boolean
}

export interface AdminPermission {
    code: string
    name?: string
    description?: string
}

export interface AdminRole {
    id: string
    name: string
    is_platform_role?: boolean
    permissions?: Array<AdminPermission | string>
    users_count?: number
}

/** Usuário de um tenant específico (tela Tenants) — mesmo shape de `role` de `AdminRoleRef`. */
export interface TenantUser {
    id: number
    name: string
    email: string
    is_active: boolean
    role: AdminRoleRef | null
}
