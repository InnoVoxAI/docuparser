export const adminKeys = {
    all: ['admin'] as const,
    users: () => [...adminKeys.all, 'users'] as const,
    roles: () => [...adminKeys.all, 'roles'] as const,
    permissions: () => [...adminKeys.all, 'permissions'] as const,
}
