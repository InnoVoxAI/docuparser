export const settingsKeys = {
    all: ['settings'] as const,
    schemas: () => [...settingsKeys.all, 'schemas'] as const,
    layouts: () => [...settingsKeys.all, 'layouts'] as const,
}
