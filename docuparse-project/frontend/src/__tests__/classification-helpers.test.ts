import { describe, it, expect } from 'vitest'
import {
    accountLabel,
    describeOrigin,
    isClassificationLocked,
    readClassificationError,
    selectableAccounts,
} from '../modules/documents/classification'

describe('selectableAccounts', () => {
    const base = { name: 'x', is_active: true }
    it('descarta contas com filhas e contas inativas, ordenando pelo código', () => {
        const result = selectableAccounts([
            { ...base, id: 'b', parent_id: 'root', code: '2.10' },
            { ...base, id: 'a', parent_id: 'root', code: '2.9' },
            { ...base, id: 'root', parent_id: null, code: '2' },
            { ...base, id: 'off', parent_id: 'root', code: '2.1', is_active: false },
        ])
        expect(result.map((account) => account.id)).toEqual(['a', 'b'])
    })

    it('uma conta cujo único filho está inativo continua sendo agrupadora', () => {
        const result = selectableAccounts([
            { ...base, id: 'root', parent_id: null, code: '2' },
            { ...base, id: 'child', parent_id: 'root', code: '2.1', is_active: false },
        ])
        expect(result).toEqual([])
    })
})

describe('classification helpers', () => {
    it('formata o rótulo da conta', () => {
        expect(accountLabel({ code: '2.1.01', name: 'Água' })).toBe('2.1.01 · Água')
    })

    it('trava a edição depois da decisão', () => {
        expect(isClassificationLocked('VALIDATION_PENDING')).toBe(false)
        expect(isClassificationLocked('EXTRACTION_COMPLETED')).toBe(false)
        for (const status of ['APPROVED', 'REJECTED', 'ERP_SENT', 'ERP_FAILED'] as const) {
            expect(isClassificationLocked(status)).toBe(true)
        }
    })

    it('descreve a origem da conta', () => {
        const base = {
            ledger_account: { id: 'a', code: '1', name: 'A' },
            rule_id: '',
            reason: '',
            updated_at: '',
        }
        expect(describeOrigin({ ...base, origin: 'automatic', classified_by: null })).toBe('Sugerida automaticamente')
        expect(describeOrigin({ ...base, origin: 'manual', classified_by: null })).toBe('Definida pelo operador')
    })

    it('lê a mensagem de validação por campo, ou cai no texto genérico', () => {
        const validation = { response: { status: 400, data: { condominium_id: ['Condomínio inativo.'] } } }
        expect(readClassificationError(validation, 'falhou')).toBe('Condomínio inativo.')
        expect(readClassificationError({ response: { status: 409, data: { detail: 'Decidido.' } } }, 'falhou')).toBe(
            'Decidido.',
        )
        expect(readClassificationError({}, 'falhou')).toBe('falhou')
    })
})
