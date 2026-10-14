import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
import {
    fetchCondominiums,
    fetchLedgerAccounts,
    setDocumentCondominium,
    setDocumentLedgerAccount,
} from '../modules/documents/services/classification.service'

const OCR = '/api/ocr'

describe('classification.service', () => {
    it('lê o plano de contas do condomínio e descarta campos extras', async () => {
        server.use(
            http.get(`${OCR}/condominiums/c1/ledger-accounts`, () =>
                HttpResponse.json([
                    { id: 'a', parent_id: null, code: '2', name: 'Despesas', is_active: true, created_at: 'x' },
                ]),
            ),
        )
        expect(await fetchLedgerAccounts('c1')).toEqual([
            { id: 'a', parent_id: null, code: '2', name: 'Despesas', is_active: true },
        ])
    })

    it('rejeita uma lista de condomínios fora do formato esperado', async () => {
        server.use(http.get(`${OCR}/condominiums`, () => HttpResponse.json([{ id: 'c1' }])))
        await expect(fetchCondominiums()).rejects.toThrow()
    })

    it('envia o override de conta e a escolha de condomínio nos endpoints do documento', async () => {
        const calls: Array<{ url: string; body: unknown }> = []
        server.use(
            http.put(`${OCR}/documents/d1/ledger-account`, async ({ request }) => {
                calls.push({ url: new URL(request.url).pathname, body: await request.json() })
                return HttpResponse.json({})
            }),
            http.put(`${OCR}/documents/d1/condominium`, async ({ request }) => {
                calls.push({ url: new URL(request.url).pathname, body: await request.json() })
                return HttpResponse.json({})
            }),
        )
        await setDocumentLedgerAccount('d1', 'acc-1')
        await setDocumentCondominium('d1', 'c1')
        expect(calls).toEqual([
            { url: `${OCR}/documents/d1/ledger-account`, body: { ledger_account_id: 'acc-1' } },
            { url: `${OCR}/documents/d1/condominium`, body: { condominium_id: 'c1' } },
        ])
    })
})
