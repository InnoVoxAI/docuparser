export const operationsKeys = {
    all: ['operations', 'dlq'] as const,
    summary: () => [...operationsKeys.all, 'summary'] as const,
    events: (stream: string) => [...operationsKeys.all, 'events', stream] as const,
}
