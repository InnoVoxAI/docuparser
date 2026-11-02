import { api } from '../../../shared/lib/http'
import {
    accountSuggestionsSchema,
    condominiumOptionsSchema,
    ledgerAccountsSchema,
    type AccountSuggestions,
    type CondominiumOption,
    type LedgerAccount,
} from '../schemas/classification'

export async function fetchCondominiums(): Promise<CondominiumOption[]> {
    const response = await api.get<unknown>('/condominiums')
    return condominiumOptionsSchema.parse(response.data)
}

export async function fetchLedgerAccounts(condominiumId: string): Promise<LedgerAccount[]> {
    const response = await api.get<unknown>(`/condominiums/${condominiumId}/ledger-accounts`)
    return ledgerAccountsSchema.parse(response.data)
}

/** Override do operador: troca a conta do documento (gera DocumentEvent no backend). */
export async function setDocumentLedgerAccount(
    documentId: string,
    ledgerAccountId: string,
    remember = false,
): Promise<void> {
    await api.put(`/documents/${documentId}/ledger-account`, {
        ledger_account_id: ledgerAccountId,
        ...(remember ? { remember } : {}),
    })
}

/** Contas que o fornecedor do documento já usou, com a evidência de cada uma. */
export async function fetchAccountSuggestions(documentId: string): Promise<AccountSuggestions> {
    const response = await api.get<unknown>(`/documents/${documentId}/account-suggestions`)
    return accountSuggestionsSchema.parse(response.data)
}

/** Define o condomínio do documento; o backend refaz a classificação nele. */
export async function setDocumentCondominium(documentId: string, condominiumId: string): Promise<void> {
    await api.put(`/documents/${documentId}/condominium`, { condominium_id: condominiumId })
}
