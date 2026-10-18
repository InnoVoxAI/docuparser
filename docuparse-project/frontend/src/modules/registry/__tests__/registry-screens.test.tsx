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

const condominium = {
    id: 'c1',
    name: 'Edificio Aurora',
    cnpj: '11222333000181',
    external_source: 'superlogica',
    external_id: '1',
    chart_of_accounts_id: 'ch1',
    is_active: true,
}
const chart = { id: 'ch1', name: 'Plano Padrao', external_source: 'superlogica', external_id: '7', is_active: true }

const batch = (status: 'running' | 'ready' | 'error', error_message = '') => ({
    id: 'b1',
    source: 'superlogica',
    status,
    error_message,
    started_by: 'op',
    created_at: '2026-10-18T10:00:00Z',
    finished_at: null,
})

function mockRegistry(overview: Record<string, unknown> = {}) {
    server.use(
        http.get(`${OCR}/condominiums`, () => HttpResponse.json([condominium])),
        http.get(`${OCR}/charts-of-accounts`, () => HttpResponse.json([chart])),
        http.get(`${OCR}/charts-of-accounts/ch1/ledger-accounts`, () =>
            HttpResponse.json([
                { id: 'a1', parent_id: null, code: '2', name: 'Despesas', is_active: true },
                { id: 'a2', parent_id: 'a1', code: '2.1', name: 'Agua', is_active: true },
            ]),
        ),
        http.get(`${OCR}/import/overview`, () =>
            HttpResponse.json({
                credentials_configured: true,
                latest_batch: null,
                pending_by_action: { new: 0, update: 0, deactivate: 0, conflict: 0 },
                pending_by_entity: { condominium: 0, chart: 0, account: 0 },
                ...overview,
            }),
        ),
    )
}

describe('Cadastros (listagem, sincronização e cadastro manual)', () => {
    beforeEach(() => localStorage.setItem('access_token', 'tok'))

    it('lista condomínios com o plano e mostra as contas do plano em árvore', async () => {
        mockMe(['inbox.view'])
        mockRegistry()
        renderApp('/registry')
        const row = (await screen.findByText('Edificio Aurora')).closest('tr') as HTMLElement
        expect(within(row).getByText('11.222.333/0001-81')).toBeInTheDocument()
        expect(within(row).getByText('Plano Padrao')).toBeInTheDocument()
        expect(within(row).getByText('Superlógica')).toBeInTheDocument()

        await userEvent.click(screen.getByRole('button', { name: /Plano Padrao/ }))
        const tree = await screen.findByRole('list', { name: 'Contas do plano' })
        expect(within(tree).getByText('Agua')).toBeInTheDocument()
    })

    it('mostra estado vazio quando não há cadastros', async () => {
        mockMe(['inbox.view'])
        mockRegistry()
        server.use(
            http.get(`${OCR}/condominiums`, () => HttpResponse.json([])),
            http.get(`${OCR}/charts-of-accounts`, () => HttpResponse.json([])),
        )
        renderApp('/registry')
        expect(await screen.findByText('Nenhum condomínio cadastrado ainda.')).toBeInTheDocument()
        expect(screen.getByText('Nenhum plano de contas cadastrado ainda.')).toBeInTheDocument()
    })

    it('mostra o erro de carregamento', async () => {
        mockMe(['inbox.view'])
        mockRegistry()
        server.use(
            http.get(`${OCR}/condominiums`, () => HttpResponse.json({ detail: 'Falha no servidor.' }, { status: 500 })),
        )
        renderApp('/registry')
        expect(await screen.findByText('Falha no servidor.')).toBeInTheDocument()
    })

    it('sem models.edit não há sincronizar nem cadastro manual', async () => {
        mockMe(['inbox.view'])
        mockRegistry()
        renderApp('/registry')
        const sync = await screen.findByRole('button', { name: /Sincronizar com Superlógica/ })
        expect(sync).toBeDisabled()
        expect(screen.queryByRole('button', { name: /Novo condomínio/ })).not.toBeInTheDocument()
    })

    it('sem credenciais o botão explica o motivo e não chama a sincronização', async () => {
        mockMe(['inbox.view', 'models.edit'])
        mockRegistry({ credentials_configured: false })
        renderApp('/registry')
        expect(await screen.findByText(/Configure as credenciais do Superlógica/)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Sincronizar com Superlógica/ })).toBeDisabled()
    })

    it('sincroniza e leva à confirmação quando há propostas', async () => {
        mockMe(['inbox.view', 'models.edit'])
        mockRegistry()
        let started = false
        server.use(
            http.post(`${OCR}/import/sync`, () => {
                started = true
                return HttpResponse.json(batch('running'), { status: 202 })
            }),
            http.get(`${OCR}/import/overview`, () =>
                HttpResponse.json({
                    credentials_configured: true,
                    latest_batch: started ? batch('ready') : null,
                    pending_by_action: { new: started ? 3 : 0, update: 0, deactivate: 0, conflict: 0 },
                    pending_by_entity: { condominium: 3, chart: 0, account: 0 },
                }),
            ),
        )
        renderApp('/registry')
        await userEvent.click(await screen.findByRole('button', { name: /Sincronizar com Superlógica/ }))
        expect(await screen.findByRole('link', { name: 'Revisar 3 propostas' })).toBeInTheDocument()
        expect(started).toBe(true)
    })

    it('mostra a falha do último lote com a mensagem legível', async () => {
        mockMe(['inbox.view', 'models.edit'])
        mockRegistry({ latest_batch: batch('error', 'O Superlógica respondeu HTTP 500 em condominios/get.') })
        renderApp('/registry')
        expect(
            await screen.findByText(/A última sincronização falhou: O Superlógica respondeu HTTP 500/),
        ).toBeInTheDocument()
    })

    it('cadastra um condomínio manualmente e mostra o erro da API em duplicidade', async () => {
        mockMe(['inbox.view', 'models.edit'])
        mockRegistry()
        const bodies: unknown[] = []
        server.use(
            http.post(`${OCR}/condominiums`, async ({ request }) => {
                bodies.push(await request.json())
                return bodies.length === 1
                    ? HttpResponse.json({ cnpj: ['Já existe um condomínio com este CNPJ.'] }, { status: 400 })
                    : HttpResponse.json({ ...condominium, id: 'c2', name: 'Novo' }, { status: 201 })
            }),
        )
        renderApp('/registry')
        await userEvent.click(await screen.findByRole('button', { name: /Novo condomínio/ }))
        const dialog = await screen.findByRole('dialog', { name: 'Novo condomínio' })

        await userEvent.click(within(dialog).getByRole('button', { name: 'Cadastrar' }))
        expect(await within(dialog).findByText('Informe o nome do condomínio.')).toBeInTheDocument()

        await userEvent.type(within(dialog).getByLabelText('Nome'), 'Novo')
        await userEvent.type(within(dialog).getByLabelText('CNPJ (opcional)'), '11222333000181')
        await userEvent.selectOptions(within(dialog).getByLabelText('Plano de contas'), 'ch1')
        await userEvent.click(within(dialog).getByRole('button', { name: 'Cadastrar' }))
        expect(await within(dialog).findByText('Já existe um condomínio com este CNPJ.')).toBeInTheDocument()

        await userEvent.click(within(dialog).getByRole('button', { name: 'Cadastrar' }))
        await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Novo condomínio' })).not.toBeInTheDocument())
        expect(bodies[1]).toEqual({ name: 'Novo', cnpj: '11222333000181', chart_of_accounts_id: 'ch1' })
    })
})
