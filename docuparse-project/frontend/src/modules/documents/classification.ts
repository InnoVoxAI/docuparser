import { asApiError, readError } from '../../shared/utils'
import type { DocumentClassification, DocumentStatus } from './types'
import type { LedgerAccount } from './schemas/classification'

/** Depois da decisão o documento segue para o ERP e a classificação não muda (espelha o backend). */
const LOCKED_STATUSES: readonly DocumentStatus[] = [
    'APPROVED',
    'REJECTED',
    'ERP_INTEGRATION_REQUESTED',
    'ERP_SENT',
    'ERP_FAILED',
]

export function isClassificationLocked(status: DocumentStatus): boolean {
    return LOCKED_STATUSES.includes(status)
}

/** Contas que recebem documentos: ativas e sem filhas (analíticas), em ordem de código. */
export function selectableAccounts(accounts: LedgerAccount[]): LedgerAccount[] {
    const parentIds = new Set(accounts.map((account) => account.parent_id).filter(Boolean))
    return accounts
        .filter((account) => account.is_active && !parentIds.has(account.id))
        .sort((a, b) => a.code.localeCompare(b.code, undefined, { numeric: true }))
}

export function accountLabel(account: { code: string; name: string }): string {
    return `${account.code} · ${account.name}`
}

export function describeOrigin(classification: DocumentClassification): string {
    if (classification.origin === 'manual') {
        return classification.classified_by ? `Definida por ${classification.classified_by}` : 'Definida pelo operador'
    }
    return classification.reason ? `Sugerida automaticamente (${classification.reason})` : 'Sugerida automaticamente'
}

/** Erros de validação do DRF vêm por campo; mostra a primeira mensagem em vez do texto genérico. */
export function readClassificationError(error: unknown, fallback: string): string {
    const data = asApiError(error).response?.data
    for (const field of ['ledger_account_id', 'condominium_id']) {
        const messages: unknown = data?.[field]
        if (Array.isArray(messages) && typeof messages[0] === 'string') return messages[0]
    }
    return readError(error, fallback)
}
