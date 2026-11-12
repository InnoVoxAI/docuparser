import type { CandidateKind, ProcessStatus } from '../schemas/payments'

export const paymentKeys = {
    all: ['payments'] as const,
    candidates: (kind: CandidateKind, search: string, page: number) =>
        [...paymentKeys.all, 'candidates', kind, search, page] as const,
    processes: (status: ProcessStatus, page: number) => [...paymentKeys.all, 'processes', status, page] as const,
}
