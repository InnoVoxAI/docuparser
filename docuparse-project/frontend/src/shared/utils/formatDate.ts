export function formatDate(value?: string | number | Date | null): string {
    if (!value) {
        return '-'
    }
    return new Intl.DateTimeFormat('pt-BR', {
        dateStyle: 'short',
        timeStyle: 'short',
    }).format(new Date(value))
}
