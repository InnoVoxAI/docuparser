import type { ProcessStatus } from '../schemas/payments'

export const paymentKeys = {
    all: ['payments'] as const,
    processes: (status: ProcessStatus, page: number) => [...paymentKeys.all, 'processes', status, page] as const,
}
