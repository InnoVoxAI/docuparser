import { asApiError, readError } from '../../shared/utils'
import type { Account, EntityType, Proposal, ProposalAction } from './schemas/registry'

export const ENTITY_LABELS: Record<EntityType, string> = {
    condominium: 'Condomínios',
    chart: 'Planos de contas',
    account: 'Contas',
}

export const ACTION_LABELS: Record<ProposalAction, string> = {
    conflict: 'Conflitos',
    new: 'Novos',
    update: 'Atualizações',
    deactivate: 'Desativações',
}

const WARNING_LABELS: Record<string, string> = {
    cnpj_invalid: 'CNPJ inválido na fonte',
    cnpj_conflict: 'CNPJ repetido em outro registro',
    administrator_cnpj: 'CNPJ da administradora, descartado',
    orphan_accounts: 'Há contas sem conta pai',
    orphan: 'Conta sem conta pai',
    duplicate: 'Duplicado de outro registro',
}

const FIELD_LABELS: Record<string, string> = {
    name: 'Nome',
    cnpj: 'CNPJ',
    is_active: 'Situação',
    chart_external_id: 'Plano de contas',
}

export function warningLabel(code: string): string {
    return WARNING_LABELS[code] ?? code
}

export function fieldLabel(field: string): string {
    return FIELD_LABELS[field] ?? field
}

export function formatCnpj(cnpj: string): string {
    return /^\d{14}$/.test(cnpj) ? cnpj.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5') : cnpj
}

export function formatValue(field: string, value: unknown): string {
    if (value === null || value === undefined || value === '') return '-'
    if (field === 'is_active') return value ? 'Ativo' : 'Inativo'
    if (field === 'cnpj') return formatCnpj(String(value))
    return String(value)
}

function text(value: unknown): string {
    return typeof value === 'string' ? value : ''
}

export interface ProposalFact {
    label: string
    value: string
}

function externalLabel(proposal: Proposal): string {
    return `Superlógica #${proposal.external_id}`
}

function list(value: unknown): string[] {
    return Array.isArray(value) ? value.map(String) : []
}

function conflictFacts(data: Proposal['data']): ProposalFact[] {
    if (data.conflict_kind === 'cnpj_taken_locally') {
        return [{ label: 'Conflito', value: 'Já existe um cadastro local com este CNPJ.' }]
    }
    const candidates = Array.isArray(data.cnpj_candidates) ? (data.cnpj_candidates as Record<string, unknown>[]) : []
    return [
        {
            label: 'Disputam o CNPJ',
            value: candidates
                .map((c) => `${text(c.name)} (${text(c.address) || 'sem endereço'}, #${text(c.external_id)})`)
                .join(' · '),
        },
    ]
}

/** Título e fatos de uma linha de proposta, sem expor o payload cru. */
export function describeProposal(proposal: Proposal): { title: string; facts: ProposalFact[] } {
    const { data } = proposal
    if (proposal.entity_type === 'account') {
        return {
            title: `${text(data.code)} ${text(data.name)}`.trim(),
            facts: [{ label: 'Plano', value: `Superlógica #${text(data.chart_external_id)}` }],
        }
    }
    if (proposal.entity_type === 'chart') {
        const accounts = Array.isArray(data.accounts) ? data.accounts.length : null
        return {
            title: text(data.name) || `Plano ${proposal.external_id}`,
            facts: [
                { label: 'Origem', value: externalLabel(proposal) },
                ...(accounts === null ? [] : [{ label: 'Contas', value: String(accounts) }]),
            ],
        }
    }
    const place = [text(data.address), text(data.city), text(data.zip_code) && `CEP ${text(data.zip_code)}`]
    const duplicates = list(data.duplicate_external_ids)
    const chartName =
        text(data.chart_name) || (text(data.chart_external_id) ? `Plano ${text(data.chart_external_id)}` : '')
    const facts: (ProposalFact | null)[] = [
        { label: 'Origem', value: externalLabel(proposal) },
        { label: 'CNPJ', value: text(data.cnpj) ? formatCnpj(text(data.cnpj)) : 'Sem CNPJ' },
        place.some(Boolean) ? { label: 'Endereço', value: place.filter(Boolean).join(', ') } : null,
        { label: 'Plano de contas', value: chartName || 'Sem plano' },
        { label: 'Situação', value: data.is_active === false ? 'Inativo' : 'Ativo' },
        duplicates.length
            ? {
                  label: 'Duplicados',
                  value: `${duplicates.map((id) => `#${id}`).join(', ')} (mesmo nome e endereço; não são importados)`,
              }
            : null,
        ...(proposal.action === 'conflict' ? conflictFacts(data) : []),
    ]
    return { title: text(data.name) || proposal.external_id, facts: facts.filter((f): f is ProposalFact => f !== null) }
}

/** Contas de uma proposta de plano novo, no formato da árvore (pai só se existir no plano). */
export function proposalAccounts(data: Proposal['data']): { accounts: Account[]; orphans: Set<string> } {
    const raw = Array.isArray(data.accounts) ? (data.accounts as Record<string, unknown>[]) : []
    const codes = new Set(raw.map((a) => text(a.code)))
    const orphans = new Set(raw.filter((a) => a.orphan === true).map((a) => text(a.code)))
    const accounts = raw.map((a) => ({
        id: text(a.code),
        parent_id: text(a.parent_code) && codes.has(text(a.parent_code)) ? text(a.parent_code) : null,
        code: text(a.code),
        name: text(a.name),
        is_active: true,
    }))
    return { accounts, orphans }
}

export function groupByAction(proposals: Proposal[]): { action: ProposalAction; items: Proposal[] }[] {
    const order: ProposalAction[] = ['conflict', 'new', 'update', 'deactivate']
    return order
        .map((action) => ({ action, items: proposals.filter((p) => p.action === action) }))
        .filter((group) => group.items.length > 0)
}

export interface AccountNode {
    account: Account
    children: AccountNode[]
}

function compareCodes(a: string, b: string): number {
    const left = a.split('.')
    const right = b.split('.')
    for (let i = 0; i < Math.max(left.length, right.length); i += 1) {
        const x = left[i]
        const y = right[i]
        if (x === undefined) return -1
        if (y === undefined) return 1
        const diff = Number(x) - Number(y)
        if (!Number.isNaN(diff) && diff !== 0) return diff
        if (Number.isNaN(diff) && x !== y) return x < y ? -1 : 1
    }
    return 0
}

/** Árvore de contas pelo `parent_id`; filhos em ordem numérica de código. */
export function buildAccountTree(accounts: Account[]): AccountNode[] {
    const nodes = new Map(accounts.map((account) => [account.id, { account, children: [] as AccountNode[] }]))
    const roots: AccountNode[] = []
    for (const node of nodes.values()) {
        const parent = node.account.parent_id ? nodes.get(node.account.parent_id) : undefined
        ;(parent ? parent.children : roots).push(node)
    }
    const sort = (list: AccountNode[]) => {
        list.sort((a, b) => compareCodes(a.account.code, b.account.code))
        list.forEach((node) => sort(node.children))
    }
    sort(roots)
    return roots
}

/** Erros de campo do DRF (`{cnpj: ["..."]}`) viram uma frase; senão, a mensagem geral. */
export function readFieldError(error: unknown, fallback: string): string {
    const data = asApiError(error).response?.data
    if (data && typeof data === 'object' && !('detail' in data)) {
        const messages = Object.values(data as Record<string, unknown>).flatMap((value) =>
            Array.isArray(value) ? value.map(String) : [],
        )
        if (messages.length) return messages.join(' ')
    }
    return readError(error, fallback)
}
