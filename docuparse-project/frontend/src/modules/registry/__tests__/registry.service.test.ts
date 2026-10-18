import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../../__tests__/mocks/server'
import {
    approveProposal,
    approveProposals,
    createCondominium,
    fetchCondominiums,
    fetchProposals,
    resolveProposal,
    startSync,
} from '../services/registry.service'
import { buildAccountTree, formatCnpj, groupByAction, readFieldError } from '../utils'
import type { Proposal } from '../schemas/registry'

const OCR = '/api/ocr'

const proposal = (overrides: Partial<Proposal> = {}): Proposal => ({
    id: 'p1',
    batch_id: 'b1',
    entity_type: 'condominium',
    external_id: '1',
    action: 'new',
    data: { name: 'Edificio A' },
    diff: {},
    warnings: [],
    status: 'pending',
    resolution: {},
    decided_by: null,
    decided_at: null,
    created_at: '2026-10-18T10:00:00Z',
    ...overrides,
})

describe('registry.service', () => {
    it('descarta campos extras e recusa formato inesperado', async () => {
        server.use(
            http.get(`${OCR}/condominiums`, () =>
                HttpResponse.json([
                    {
                        id: 'c1',
                        name: 'Edificio A',
                        cnpj: '11222333000181',
                        external_source: 'superlogica',
                        external_id: '1',
                        chart_of_accounts_id: null,
                        is_active: true,
                        aliases: ['x'],
                    },
                ]),
            ),
        )
        const [condominium] = await fetchCondominiums()
        expect(condominium).not.toHaveProperty('aliases')

        server.use(http.get(`${OCR}/condominiums`, () => HttpResponse.json([{ id: 'c1' }])))
        await expect(fetchCondominiums()).rejects.toThrow()
    })

    it('envia o cadastro manual com o plano escolhido', async () => {
        let body: unknown
        server.use(
            http.post(`${OCR}/condominiums`, async ({ request }) => {
                body = await request.json()
                return HttpResponse.json(
                    {
                        id: 'c1',
                        name: 'Novo',
                        cnpj: '',
                        external_source: '',
                        external_id: '',
                        chart_of_accounts_id: 'ch1',
                        is_active: true,
                    },
                    { status: 201 },
                )
            }),
        )
        await createCondominium({ name: 'Novo', cnpj: '', chart_of_accounts_id: 'ch1' })
        expect(body).toEqual({ name: 'Novo', cnpj: '', chart_of_accounts_id: 'ch1' })
    })

    it('inicia a sincronização, lista propostas por tipo e decide', async () => {
        const calls: string[] = []
        server.use(
            http.post(`${OCR}/import/sync`, () => {
                calls.push('sync')
                return HttpResponse.json(
                    {
                        id: 'b1',
                        source: 'superlogica',
                        status: 'running',
                        error_message: '',
                        started_by: 'op',
                        created_at: '2026-10-18T10:00:00Z',
                        finished_at: null,
                    },
                    { status: 202 },
                )
            }),
            http.get(`${OCR}/import/proposals`, ({ request }) => {
                const url = new URL(request.url)
                calls.push(`list:${url.searchParams.get('entity_type')}:${url.searchParams.get('offset')}`)
                return HttpResponse.json({ count: 1, results: [proposal()] })
            }),
            http.post(`${OCR}/import/proposals/p1/approve`, () => {
                calls.push('approve')
                return HttpResponse.json(proposal({ status: 'approved' }))
            }),
            http.post(`${OCR}/import/proposals/approve`, async ({ request }) => {
                calls.push(`bulk:${JSON.stringify(await request.json())}`)
                return HttpResponse.json({
                    done: [proposal()],
                    failed: [{ id: 'p2', detail: 'Aprove o plano antes.' }],
                })
            }),
            http.post(`${OCR}/import/proposals/p1/resolve`, async ({ request }) => {
                calls.push(`resolve:${JSON.stringify(await request.json())}`)
                return HttpResponse.json([proposal({ status: 'resolved' })])
            }),
        )

        expect((await startSync()).status).toBe('running')
        expect((await fetchProposals({ entityType: 'chart', offset: 100 })).count).toBe(1)
        expect((await approveProposal('p1')).status).toBe('approved')
        expect((await approveProposals(['p1', 'p2'])).failed[0].detail).toBe('Aprove o plano antes.')
        expect(await resolveProposal('p1', { cnpj_owner: null })).toHaveLength(1)
        expect(calls).toEqual([
            'sync',
            'list:chart:100',
            'approve',
            'bulk:{"ids":["p1","p2"]}',
            'resolve:{"resolution":{"cnpj_owner":null}}',
        ])
    })
})

describe('registry utils', () => {
    it('monta a árvore de contas em ordem numérica de código', () => {
        const tree = buildAccountTree([
            { id: 'c', parent_id: 'a', code: '2.10', name: 'Dez', is_active: true },
            { id: 'b', parent_id: 'a', code: '2.2', name: 'Dois', is_active: true },
            { id: 'a', parent_id: null, code: '2', name: 'Despesas', is_active: true },
        ])
        expect(tree).toHaveLength(1)
        expect(tree[0].children.map((node) => node.account.code)).toEqual(['2.2', '2.10'])
    })

    it('agrupa por ação, conflitos primeiro, e formata o CNPJ', () => {
        const groups = groupByAction([
            proposal({ id: 'a', action: 'update' }),
            proposal({ id: 'b', action: 'conflict' }),
            proposal({ id: 'c', action: 'new' }),
        ])
        expect(groups.map((group) => group.action)).toEqual(['conflict', 'new', 'update'])
        expect(formatCnpj('11222333000181')).toBe('11.222.333/0001-81')
        expect(formatCnpj('abc')).toBe('abc')
    })

    it('transforma erros de campo do DRF em uma frase', () => {
        const error = { response: { status: 400, data: { cnpj: ['Já existe um condomínio com este CNPJ.'] } } }
        expect(readFieldError(error, 'falhou')).toBe('Já existe um condomínio com este CNPJ.')
        expect(readFieldError({ response: { data: { detail: 'Sem permissão.' } } }, 'falhou')).toBe('Sem permissão.')
    })
})
