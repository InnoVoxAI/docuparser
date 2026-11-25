import type { PaymentDocumentDetail } from './schemas/payments'
import { formatCnpj, formatMoney } from './utils'

type Format = 'text' | 'money' | 'date' | 'tax_id' | 'code'

export interface FieldSpec {
    label: string
    /** Primeiro campo com valor vence (o mesmo dado pode vir com nomes diferentes). */
    keys: string[]
    format?: Format
    /** Ocupa a linha toda (textos e códigos longos). */
    wide?: boolean
    /** Destaque visual para o dado que decide o casamento. */
    strong?: boolean
}

export const INVOICE_FIELDS: FieldSpec[] = [
    { label: 'Valor da nota', keys: ['valor_nota'], format: 'money', strong: true },
    { label: 'Fornecedor', keys: ['fornecedor_nome'] },
    { label: 'CNPJ do fornecedor', keys: ['cnpj_fornecedor', 'cpf_fornecedor'], format: 'tax_id', strong: true },
    { label: 'Tomador', keys: ['tomador_nome'] },
    { label: 'CNPJ do tomador', keys: ['cnpj_tomador', 'cpf_tomador'], format: 'tax_id' },
    { label: 'Número da nota', keys: ['numero_nota'] },
    { label: 'Emissão', keys: ['data_emissao'], format: 'date' },
    { label: 'Competência', keys: ['competencia'] },
    { label: 'Valor líquido', keys: ['valor_liquido'], format: 'money' },
    { label: 'Descrição do serviço', keys: ['descricao_servico'], wide: true },
]

export const BOLETO_FIELDS: FieldSpec[] = [
    { label: 'Valor do boleto', keys: ['valor_boleto', 'valor_documento'], format: 'money', strong: true },
    { label: 'Vencimento', keys: ['data_vencimento'], format: 'date', strong: true },
    { label: 'Beneficiário', keys: ['beneficiario_nome'] },
    { label: 'CNPJ do beneficiário', keys: ['cnpj_cpf_beneficiario'], format: 'tax_id', strong: true },
    { label: 'Pagador', keys: ['pagador_nome'] },
    { label: 'CNPJ do pagador', keys: ['cnpj_cpf_pagador'], format: 'tax_id' },
    { label: 'Nº do documento', keys: ['numero_documento'] },
    { label: 'Emissão', keys: ['data_documento'], format: 'date' },
    { label: 'Banco', keys: ['nome_banco', 'instituicao_cobranca'] },
    { label: 'Valor cobrado', keys: ['valor_cobrado'], format: 'money' },
    { label: 'Multa', keys: ['multa'] },
    { label: 'Juros', keys: ['juros'] },
    { label: 'Linha digitável', keys: ['linha_digitavel'], format: 'code', wide: true },
]

const NOT_FOUND = 'valor não encontrado'

/** Valor simples de um campo extraído, que chega como `{value, confidence}` ou direto. */
export function rawField(detail: PaymentDocumentDetail | undefined, keys: string[]): string {
    const fields = detail?.extraction_result?.fields ?? {}
    for (const key of keys) {
        const entry = fields[key]
        const value =
            entry !== null && typeof entry === 'object' && 'value' in entry
                ? (entry as { value: unknown }).value
                : entry
        const text = value === null || value === undefined ? '' : String(value).trim()
        if (text && text.toLowerCase() !== NOT_FOUND) return text
    }
    return ''
}

/** Valor monetário lido do texto extraído ("1.000,50" ou "1000.50"), em número, ou null. */
export function moneyOf(text: string): number | null {
    if (!text) return null
    const clean = text.replace(/R\$|\s/g, '')
    const parsed = Number(clean.includes(',') ? clean.replace(/\./g, '').replace(',', '.') : clean)
    return Number.isFinite(parsed) ? parsed : null
}

/** Dia do vencimento no formato ISO (aceita 2026-07-20 e 20/07/2026), ou ''. */
export function isoDate(text: string): string {
    const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(text)
    if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`
    const br = /^(\d{2})\/(\d{2})\/(\d{4})/.exec(text)
    return br ? `${br[3]}-${br[2]}-${br[1]}` : ''
}

export function formatIso(iso: string): string {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
    return match ? `${match[3]}/${match[2]}/${match[1]}` : iso
}

export function digitsOf(text: string): string {
    return text.replace(/\D/g, '')
}

function formatCpf(digits: string): string {
    return digits.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4')
}

/** Texto pronto para mostrar. Vazio quando o campo não foi lido. */
export function displayField(detail: PaymentDocumentDetail | undefined, spec: FieldSpec): string {
    const text = rawField(detail, spec.keys)
    if (!text) return ''
    if (spec.format === 'money') {
        const amount = moneyOf(text)
        return amount === null ? text : formatMoney(amount.toFixed(2))
    }
    if (spec.format === 'date') return formatIso(isoDate(text)) || text
    if (spec.format === 'tax_id') {
        const digits = digitsOf(text)
        return digits.length === 11 ? formatCpf(digits) : formatCnpj(digits)
    }
    return text
}
