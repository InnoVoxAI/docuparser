import type { Account } from './schemas/registry'
import type { Rule } from './schemas/rules'
import { formatCnpj } from './utils'

export const ORIGIN_LABELS: Record<string, string> = {
    history: 'Histórico do ERP',
    learned: 'Aprendida com analistas',
    manual: 'Manual',
}

export function formatTaxId(taxId: string): string {
    if (taxId.length === 14) return formatCnpj(taxId)
    if (taxId.length === 11) return taxId.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4')
    return taxId
}

/** Fornecedor da regra: o CNPJ/CPF (com o trecho, se houver) ou o nome que ela procura no documento. */
export function describeRuleSupplier(rule: Rule): { title: string; detail: string } {
    if (rule.supplier_tax_id) {
        return {
            title: formatTaxId(rule.supplier_tax_id),
            detail: rule.keyword ? `só se o documento tiver "${rule.keyword}"` : '',
        }
    }
    return { title: rule.keyword, detail: 'por nome no documento' }
}

/** Quantas vezes o fornecedor foi para esta conta, de quantas no total. */
export function describeRuleEvidence(rule: Rule): string {
    if (rule.evidence_total === 0) return rule.origin === 'manual' ? 'Cadastrada à mão' : 'Sem evidência'
    const share = Math.round((100 * rule.evidence_count) / rule.evidence_total)
    return `${rule.evidence_count} de ${rule.evidence_total} (${share}%)`
}

/** Por que a regra não pré-preenche, para o analista não ter que adivinhar. */
export function whyNotPrefilled(rule: Rule): string {
    if (rule.prefills) return ''
    if (!rule.is_active) return 'Desativada'
    return 'Evidência insuficiente (precisa de 3 lançamentos e 90% de concordância)'
}

/** Contas que recebem documentos: ativas, de despesa (grupo 2) e sem filhas, em ordem de código. */
export function leafExpenseAccounts(accounts: Account[]): Account[] {
    const parentIds = new Set(accounts.map((account) => account.parent_id).filter(Boolean))
    return accounts
        .filter((a) => a.is_active && a.code.startsWith('2') && !parentIds.has(a.id))
        .sort((a, b) => a.code.localeCompare(b.code, undefined, { numeric: true }))
}
