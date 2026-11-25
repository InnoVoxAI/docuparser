import { digitsOf, formatIso, isoDate, rawField } from './documentFields'
import type { PaymentDocument, PaymentDocumentDetail } from './schemas/payments'
import { describeCoverage, formatCnpj } from './utils'

export type CheckTone = 'ok' | 'warn' | 'info'

export interface Check {
    id: string
    label: string
    tone: CheckTone
    text: string
}

type Details = Record<string, PaymentDocumentDetail | undefined>

function cnpjCheck(invoice: PaymentDocument, boletos: PaymentDocument[]): Check {
    const label = 'CNPJ do fornecedor'
    if (!invoice.tax_id || boletos.some((b) => !b.tax_id)) {
        return { id: 'cnpj', label, tone: 'warn', text: 'Algum CNPJ não foi lido; confira nos documentos.' }
    }
    if (boletos.every((b) => b.tax_id === invoice.tax_id)) {
        return { id: 'cnpj', label, tone: 'ok', text: `Igual na nota e nos boletos (${formatCnpj(invoice.tax_id)}).` }
    }
    return { id: 'cnpj', label, tone: 'warn', text: 'O CNPJ de algum boleto é diferente do CNPJ da nota.' }
}

function valueCheck(invoice: PaymentDocument, boletos: PaymentDocument[]): Check {
    const label = 'Valor'
    if (invoice.amount === null || boletos.some((b) => b.amount === null)) {
        return { id: 'value', label, tone: 'warn', text: 'Algum valor não foi lido; confira nos documentos.' }
    }
    const total = boletos.reduce((sum, b) => sum + Number(b.amount), 0)
    const diff = Number(invoice.amount) - total
    const tone: CheckTone = Math.abs(diff) < 0.005 ? 'ok' : diff > 0 ? 'info' : 'warn'
    return { id: 'value', label, tone, text: describeCoverage(invoice.amount, total.toFixed(2)) }
}

/** O boleto precisa ser cobrado do mesmo condomínio que a nota atende (tomador = pagador). */
function payerCheck(invoice: PaymentDocument, boletos: PaymentDocument[], details: Details): Check | null {
    if (!details[invoice.id] || boletos.some((b) => !details[b.id])) return null
    const label = 'Pagador × tomador'
    const taker = digitsOf(rawField(details[invoice.id], ['cnpj_tomador', 'cpf_tomador']))
    const payers = boletos.map((b) => digitsOf(rawField(details[b.id], ['cnpj_cpf_pagador'])))
    if (!taker || payers.every((p) => !p)) {
        return { id: 'payer', label, tone: 'info', text: 'O pagador ou o tomador não foi lido.' }
    }
    const different = payers.filter((p) => p && p !== taker).length
    if (different === 0) {
        return {
            id: 'payer',
            label,
            tone: 'ok',
            text: `O pagador dos boletos é o tomador da nota (${formatCnpj(taker)}).`,
        }
    }
    return {
        id: 'payer',
        label,
        tone: 'warn',
        text: `O pagador de ${different} boleto(s) é diferente do tomador da nota: pode ser de outro condomínio.`,
    }
}

function dueCheck(boletos: PaymentDocument[], details: Details): Check | null {
    if (boletos.some((b) => !details[b.id])) return null
    const dates = boletos.map((b) => isoDate(rawField(details[b.id], ['data_vencimento'])))
    const read = dates.filter(Boolean).sort()
    const label = 'Vencimentos'
    if (read.length < boletos.length) {
        return { id: 'due', label, tone: 'warn', text: 'Algum boleto está sem vencimento lido.' }
    }
    return { id: 'due', label, tone: 'info', text: read.map(formatIso).join(' · ') }
}

function originCheck(invoice: PaymentDocument, boletos: PaymentDocument[]): Check {
    const together =
        Boolean(invoice.source_thread_id) && boletos.every((b) => b.source_thread_id === invoice.source_thread_id)
    return {
        id: 'origin',
        label: 'Origem',
        tone: together ? 'ok' : 'info',
        text: together ? 'Os documentos chegaram juntos (mesma origem).' : 'Os documentos chegaram separados.',
    }
}

function condominiumCheck(invoice: PaymentDocument, details: Details): Check | null {
    const detail = details[invoice.id]
    if (!detail) return null
    const label = 'Condomínio'
    if (!detail.condominium) {
        return { id: 'condominium', label, tone: 'warn', text: 'O condomínio da nota não foi identificado.' }
    }
    const account = detail.classification?.ledger_account
    const suffix = account ? ` · Conta ${account.code} ${account.name}` : ''
    return { id: 'condominium', label, tone: 'info', text: `${detail.condominium.name}${suffix}` }
}

/** O que o analista confere ao decidir: o que casa, o que diverge e o que ainda não foi lido. */
export function buildChecks(invoice: PaymentDocument | null, boletos: PaymentDocument[], details: Details): Check[] {
    if (!invoice || boletos.length === 0) return []
    return [
        cnpjCheck(invoice, boletos),
        valueCheck(invoice, boletos),
        payerCheck(invoice, boletos, details),
        dueCheck(boletos, details),
        originCheck(invoice, boletos),
        condominiumCheck(invoice, details),
    ].filter((check): check is Check => check !== null)
}
