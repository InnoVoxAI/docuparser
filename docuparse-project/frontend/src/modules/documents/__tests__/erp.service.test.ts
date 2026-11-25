import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../../__tests__/mocks/server'
import { confirmErpSend, fetchErpDetail, retryErpSend } from '../services/erp.service'

const OCR = '/api/ocr'

const valid = {
    state: 'sent',
    mode: 'sandbox',
    dry_run: false,
    confirmation_required: true,
    summary: null,
    errors: [],
    reason: '',
    code: '',
    attempts: 0,
    max_attempts: 5,
    retryable: false,
    exhausted: false,
    can_retry: false,
    next_retry_at: null,
    external_id: '9001',
    can_confirm: false,
    can_send: true,
}

describe('erp.service', () => {
    it('lê o estado do lançamento', async () => {
        server.use(http.get(`${OCR}/documents/d1/erp`, () => HttpResponse.json(valid)))
        expect((await fetchErpDetail('d1')).external_id).toBe('9001')
    })

    it('confirma e reenvia pelos endpoints certos', async () => {
        const calls: string[] = []
        server.use(
            http.post(`${OCR}/documents/d1/erp/confirm`, () => {
                calls.push('confirm')
                return HttpResponse.json(valid, { status: 202 })
            }),
            http.post(`${OCR}/documents/d1/erp/retry`, () => {
                calls.push('retry')
                return HttpResponse.json(valid, { status: 202 })
            }),
        )
        await confirmErpSend('d1')
        await retryErpSend('d1')
        expect(calls).toEqual(['confirm', 'retry'])
    })

    it('recusa uma resposta fora do contrato em vez de mostrar dado quebrado', async () => {
        server.use(http.get(`${OCR}/documents/d1/erp`, () => HttpResponse.json({ ...valid, state: 'inventado' })))
        await expect(fetchErpDetail('d1')).rejects.toThrow()
    })
})
