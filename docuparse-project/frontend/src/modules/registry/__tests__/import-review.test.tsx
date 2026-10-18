import { beforeEach, describe, expect, it } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../../__tests__/mocks/server'
import { renderApp } from '../../../__tests__/utils'

const OCR = '/api/ocr'

function mockMe(permissions: string[]) {
    server.use(
        http.get('/api/auth/me', () =>
            HttpResponse.json({ id: 'u1', name: 'User', email: 'u@docuparse.local', permissions }),
        ),
    )
}

const base = {
    batch_id: 'b1',
    status: 'pending',
    resolution: {},
    decided_by: null,
    decided_at: null,
    created_at: '2026-10-18T10:00:00Z',
    warnings: [] as string[],
    diff: {},
}

const created = {
    ...base,
    id: 'p-new',
    entity_type: 'condominium',
    external_id: '10',
    action: 'new',
    data: { name: 'Edificio Novo', cnpj: '11222333000181', chart_external_id: '7', address: 'Rua 1, 10' },
}
const renamed = {
    ...base,
    id: 'p-upd',
    entity_type: 'condominium',
    external_id: '11',
    action: 'update',
    data: { name: 'Edificio Renomeado' },
    diff: { name: { from: 'Edificio Antigo', to: 'Edificio Renomeado' }, is_active: { from: true, to: false } },
    warnings: ['duplicate'],
}
const conflictFor = (id: string, name: string, address: string) => ({
    ...base,
    id,
    entity_type: 'condominium',
    external_id: id === 'p-c1' ? '20' : '21',
    action: 'conflict',
    data: {
        name,
        cnpj: '',
        source_cnpj: '11222333000181',
        conflict_kind: 'cnpj_duplicated',
        cnpj_candidates: [
            { external_id: '20', name: 'Edificio A', address: 'Rua A' },
            { external_id: '21', name: 'Edificio B', address: 'Rua B' },
        ],
        address,
    },
    warnings: ['cnpj_conflict'],
})

function mockReview(results: unknown[], counts = { condominium: results.length, chart: 0, account: 0 }) {
    server.use(
        http.get(`${OCR}/import/overview`, () =>
            HttpResponse.json({
                credentials_configured: true,
                latest_batch: null,
                pending_by_action: { new: 1, update: 1, deactivate: 0, conflict: 0 },
                pending_by_entity: counts,
            }),
        ),
        http.get(`${OCR}/import/proposals`, () => HttpResponse.json({ count: results.length, results })),
        http.get(`${OCR}/condominiums`, () => HttpResponse.json([])),
    )
}

describe('Confirmação da importação', () => {
    beforeEach(() => localStorage.setItem('access_token', 'tok'))

    it('agrupa por ação e mostra diferenças e avisos', async () => {
        mockMe(['inbox.view', 'models.edit'])
        mockReview([created, renamed])
        renderApp('/registry-import')

        const news = await screen.findByRole('region', { name: 'Novos' })
        expect(within(news).getByText('Edificio Novo')).toBeInTheDocument()
        expect(within(news).getByText(/11\.222\.333\/0001-81/)).toBeInTheDocument()

        const updates = screen.getByRole('region', { name: 'Atualizações' })
        const diffs = within(updates).getByRole('list', { name: 'Diferenças' })
        expect(within(diffs).getByText('Edificio Antigo')).toBeInTheDocument()
        expect(within(diffs).getByText('Inativo')).toBeInTheDocument()
        expect(within(updates).getByText('Duplicado de outro registro')).toBeInTheDocument()
    })

    it('confirma e rejeita uma proposta por linha', async () => {
        mockMe(['inbox.view', 'models.edit'])
        mockReview([created, renamed])
        const calls: string[] = []
        server.use(
            http.post(`${OCR}/import/proposals/:id/:decision`, ({ params }) => {
                calls.push(`${params.id}:${params.decision}`)
                return HttpResponse.json({ ...created, status: 'approved' })
            }),
        )
        renderApp('/registry-import')
        const news = await screen.findByRole('region', { name: 'Novos' })
        await userEvent.click(within(news).getByRole('button', { name: 'Confirmar' }))
        const updates = screen.getByRole('region', { name: 'Atualizações' })
        await userEvent.click(within(updates).getByRole('button', { name: 'Rejeitar' }))
        await waitFor(() => expect(calls).toEqual(['p-new:approve', 'p-upd:reject']))
    })

    it('confirma em lote só as selecionadas e mostra as que falharam', async () => {
        mockMe(['inbox.view', 'models.edit'])
        mockReview([created, renamed])
        let body: unknown
        server.use(
            http.post(`${OCR}/import/proposals/approve`, async ({ request }) => {
                body = await request.json()
                return HttpResponse.json({
                    done: [{ ...created, status: 'approved' }],
                    failed: [{ id: 'p-upd', detail: 'Aprove o plano de contas 7 antes dos itens que dependem dele.' }],
                })
            }),
        )
        renderApp('/registry-import')
        await screen.findByRole('region', { name: 'Novos' })
        expect(screen.queryByRole('button', { name: /Confirmar selecionadas/ })).not.toBeInTheDocument()

        await userEvent.click(screen.getByLabelText('Selecionar 10'))
        await userEvent.click(screen.getByLabelText('Selecionar 11'))
        await userEvent.click(screen.getByRole('button', { name: /Confirmar selecionadas/ }))
        const dialog = await screen.findByRole('dialog')
        await userEvent.click(within(dialog).getByRole('button', { name: 'Confirmar' }))

        expect(await screen.findByText(/1 não puderam ser concluídas/)).toBeInTheDocument()
        expect(screen.getByText(/Aprove o plano de contas 7 antes/)).toBeInTheDocument()
        expect(body).toEqual({ ids: ['p-new', 'p-upd'] })
    })

    it('resolve um conflito de CNPJ escolhendo quem fica com ele', async () => {
        mockMe(['inbox.view', 'models.edit'])
        mockReview([conflictFor('p-c1', 'Edificio A', 'Rua A'), conflictFor('p-c2', 'Edificio B', 'Rua B')])
        let sent: unknown
        server.use(
            http.post(`${OCR}/import/proposals/p-c1/resolve`, async ({ request }) => {
                sent = await request.json()
                return HttpResponse.json([{ ...conflictFor('p-c1', 'Edificio A', 'Rua A'), status: 'resolved' }])
            }),
        )
        renderApp('/registry-import')
        const conflicts = await screen.findByRole('region', { name: 'Conflitos' })
        expect(within(conflicts).queryByLabelText(/Selecionar/)).not.toBeInTheDocument()
        await userEvent.click(within(conflicts).getAllByRole('button', { name: 'Resolver' })[0])

        const dialog = await screen.findByRole('dialog', { name: 'Resolver conflito de CNPJ' })
        expect(within(dialog).getByText('Conflito de CNPJ 11.222.333/0001-81')).toBeInTheDocument()
        await userEvent.click(within(dialog).getByRole('button', { name: 'Resolver' }))
        expect(await within(dialog).findByText('Escolha uma opção.')).toBeInTheDocument()

        await userEvent.click(within(dialog).getByLabelText('CNPJ fica com Edificio B'))
        await userEvent.click(within(dialog).getByRole('button', { name: 'Resolver' }))
        await waitFor(() => expect(sent).toEqual({ resolution: { cnpj_owner: '21' } }))
    })

    it('"nenhum fica com o CNPJ" envia owner nulo', async () => {
        mockMe(['inbox.view', 'models.edit'])
        mockReview([conflictFor('p-c1', 'Edificio A', 'Rua A')])
        let sent: unknown
        server.use(
            http.post(`${OCR}/import/proposals/p-c1/resolve`, async ({ request }) => {
                sent = await request.json()
                return HttpResponse.json([])
            }),
        )
        renderApp('/registry-import')
        await userEvent.click(await screen.findByRole('button', { name: 'Resolver' }))
        const dialog = await screen.findByRole('dialog', { name: 'Resolver conflito de CNPJ' })
        await userEvent.click(within(dialog).getByLabelText('Nenhum fica com o CNPJ'))
        await userEvent.click(within(dialog).getByRole('button', { name: 'Resolver' }))
        await waitFor(() => expect(sent).toEqual({ resolution: { cnpj_owner: null } }))
    })

    it('mostra a mensagem da API quando a decisão é recusada', async () => {
        mockMe(['inbox.view', 'models.edit'])
        mockReview([created])
        server.use(
            http.post(`${OCR}/import/proposals/p-new/approve`, () =>
                HttpResponse.json(
                    { detail: 'Aprove o plano de contas 7 antes dos itens que dependem dele.' },
                    { status: 409 },
                ),
            ),
        )
        renderApp('/registry-import')
        await userEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))
        expect(await screen.findByText(/Aprove o plano de contas 7 antes/)).toBeInTheDocument()
    })

    it('mostra estado vazio quando nada está pendente', async () => {
        mockMe(['inbox.view'])
        mockReview([])
        renderApp('/registry-import')
        expect(await screen.findByText('Nada pendente de confirmação nesta aba.')).toBeInTheDocument()
    })

    it('quem só consulta vê as propostas, sem ações habilitadas', async () => {
        mockMe(['inbox.view'])
        mockReview([created])
        renderApp('/registry-import')
        const news = await screen.findByRole('region', { name: 'Novos' })
        expect(within(news).getByRole('button', { name: 'Confirmar' })).toBeDisabled()
        expect(within(news).getByRole('button', { name: 'Rejeitar' })).toBeDisabled()
        expect(screen.getByText(/confirmar exige permissão de edição/)).toBeInTheDocument()
        expect(screen.queryByLabelText('Selecionar 10')).not.toBeInTheDocument()
    })
})
