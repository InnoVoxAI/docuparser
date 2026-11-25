import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryRouter } from 'react-router'
import { AuthProvider } from '../../auth'
import { PaymentsView } from '../components/PaymentsView'
import { server } from '../../../__tests__/mocks/server'
import { renderApp } from '../../../__tests__/utils'
import { boletoDoc, invoiceDoc, process } from './fixtures'

// Popup com a nota e os boletos lado a lado, nas telas de Pagamentos.
const OCR = '/api/ocr'

function mockMe(permissions: string[]) {
    server.use(
        http.get('/api/auth/me', () =>
            HttpResponse.json({ id: 'u1', name: 'User', email: 'u@docuparse.local', permissions }),
        ),
    )
}

const page = (results: ReturnType<typeof process>[]) => ({
    results,
    count: results.length,
    page: 1,
    page_size: 10,
    total_pages: results.length ? 1 : 0,
})

const field = (value: string) => ({ value, confidence: 1 })

const invoiceDetail = {
    id: 'd1',
    original_filename: 'nota.pdf',
    content_type: 'application/pdf',
    status: 'VALIDATION_PENDING',
    channel: 'email',
    received_at: '2026-11-10T10:00:00Z',
    source_thread_id: 'email:<msg-1@example.test>',
    extraction_result: {
        fields: {
            valor_nota: field('900,00'),
            fornecedor_nome: field('Fornecedor Exemplo LTDA'),
            cnpj_fornecedor: field('09.769.035/0001-64'),
            tomador_nome: field('Condomínio Exemplo'),
            cnpj_tomador: field('11.222.333/0001-81'),
            numero_nota: field('4051'),
            data_emissao: field('01/07/2026'),
            descricao_servico: field('Manutenção predial mensal'),
        },
    },
    condominium: { id: 'c1', name: 'Edifício Exemplo' },
    classification: { ledger_account: { code: '2.1.02', name: 'Manutenção' } },
}

function boletoDetail(id: string, name: string, due: string, payer = '11.222.333/0001-81') {
    return {
        id,
        original_filename: name,
        content_type: 'application/pdf',
        status: 'VALIDATION_PENDING',
        channel: 'email',
        received_at: '2026-11-10T10:00:00Z',
        source_thread_id: 'email:<msg-1@example.test>',
        extraction_result: {
            fields: {
                valor_boleto: field('300,00'),
                data_vencimento: field(due),
                beneficiario_nome: field('Fornecedor Exemplo LTDA'),
                cnpj_cpf_beneficiario: field('09.769.035/0001-64'),
                cnpj_cpf_pagador: field(payer),
                linha_digitavel: field('34191.79001 01043.510047 91020.150008 1 96610000030000'),
            },
        },
        condominium: null,
        classification: null,
    }
}

function mockDetails(overrides: Record<string, unknown> = {}) {
    const details: Record<string, unknown> = {
        d1: invoiceDetail,
        b1: boletoDetail('b1', 'boleto-1.pdf', '2026-08-20'),
        b2: boletoDetail('b2', 'boleto-2.pdf', '2026-07-10'),
        ...overrides,
    }
    server.use(
        http.get(`${OCR}/documents/:id`, ({ params }) => {
            const body = details[String(params.id)]
            return body ? HttpResponse.json(body) : new HttpResponse(null, { status: 404 })
        }),
    )
}

/**
 * O jsdom não consegue navegar de verdade com o React Router (o `Request` do Node recusa o
 * AbortSignal dele). Nos testes de "Corrigir dados" a navegação é capturada: o que importa é
 * para onde o atalho aponta. A Visão Geral de verdade é quem lê o parâmetro (testada à parte).
 */
const navigation = vi.hoisted(() => ({ spy: null as null | ((...args: unknown[]) => void) }))
vi.mock('react-router', async (importOriginal) => {
    const actual = await importOriginal<typeof import('react-router')>()
    return {
        ...actual,
        useNavigate: () => {
            const real = actual.useNavigate()
            return (...args: unknown[]) =>
                navigation.spy ? navigation.spy(...args) : (real as (...a: unknown[]) => void)(...args)
        },
    }
})

function renderPaymentsCapturingNavigation() {
    const navigate = vi.fn()
    navigation.spy = navigate
    const router = createMemoryRouter([{ path: '/', element: <PaymentsView /> }], { initialEntries: ['/'] })
    render(
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
            <AuthProvider>
                <RouterProvider router={router} />
            </AuthProvider>
        </QueryClientProvider>,
    )
    return navigate
}

async function openCardDialog(buttonName: string | RegExp = 'Ver documentos') {
    renderApp('/payments')
    const card = await screen.findByRole('article', { name: 'Processo de pagamento' })
    await userEvent.click(within(card).getByRole('button', { name: buttonName }))
    return screen.findByRole('dialog', { name: 'Documentos do processo' })
}

describe('Pagamentos: documentos lado a lado', () => {
    beforeEach(() => {
        navigation.spy = null
        localStorage.setItem('access_token', 'tok')
        URL.createObjectURL = vi.fn(() => 'blob:preview')
        URL.revokeObjectURL = vi.fn()
        mockMe(['inbox.view', 'documents.validate'])
        server.use(http.get(`${OCR}/payment-processes`, () => HttpResponse.json(page([process()]))))
        mockDetails()
    })

    it('mostra a nota e o boleto lado a lado com os campos importantes', async () => {
        const dialog = await openCardDialog()

        const invoice = await within(dialog).findByRole('region', { name: 'Nota fiscal: nota.pdf' })
        const boleto = within(dialog).getByRole('region', { name: 'Boleto: boleto-1.pdf' })
        expect(await within(invoice).findByText('Fornecedor Exemplo LTDA')).toBeInTheDocument()
        expect(within(invoice).getByText('09.769.035/0001-64')).toBeInTheDocument()
        expect(within(invoice).getByText('Manutenção predial mensal')).toBeInTheDocument()
        expect(within(invoice).getByText('01/07/2026')).toBeInTheDocument()
        expect(await within(boleto).findByText('20/08/2026')).toBeInTheDocument()
        expect(within(boleto).getByText(/34191\.79001/)).toBeInTheDocument()
    })

    it('mostra a conferência: o que casa, o que falta e os vencimentos em ordem', async () => {
        const dialog = await openCardDialog()

        const checks = await within(dialog).findByRole('list', { name: 'Conferência' })
        expect(within(checks).getByText(/Igual na nota e nos boletos/)).toBeInTheDocument()
        expect(within(checks).getByText(/Faltam/)).toBeInTheDocument()
        expect(await within(checks).findByText('10/07/2026 · 20/08/2026')).toBeInTheDocument()
        expect(within(checks).getByText(/O pagador dos boletos é o tomador da nota/)).toBeInTheDocument()
        expect(within(checks).getByText(/Edifício Exemplo · Conta 2\.1\.02 Manutenção/)).toBeInTheDocument()
    })

    it('avisa quando o pagador do boleto não é o tomador da nota', async () => {
        mockDetails({ b1: boletoDetail('b1', 'boleto-1.pdf', '2026-08-20', '44.555.666/0001-00') })
        const dialog = await openCardDialog()
        expect(await within(dialog).findByText(/pode ser de outro condomínio/)).toBeInTheDocument()
    })

    it('com vários boletos, troca de boleto pelas abas', async () => {
        const dialog = await openCardDialog()
        expect(within(dialog).getByRole('region', { name: 'Boleto: boleto-1.pdf' })).toBeInTheDocument()

        await userEvent.click(within(dialog).getByRole('tab', { name: /Boleto 2/ }))

        expect(within(dialog).getByRole('region', { name: 'Boleto: boleto-2.pdf' })).toBeInTheDocument()
        expect(within(dialog).queryByRole('region', { name: 'Boleto: boleto-1.pdf' })).not.toBeInTheDocument()
    })

    it('clicar no nome de um boleto abre o popup já nesse boleto', async () => {
        renderApp('/payments')
        const card = await screen.findByRole('article', { name: 'Processo de pagamento' })
        await userEvent.click(within(card).getByRole('button', { name: /boleto-2\.pdf/ }))

        const dialog = await screen.findByRole('dialog', { name: 'Documentos do processo' })
        expect(within(dialog).getByRole('region', { name: 'Boleto: boleto-2.pdf' })).toBeInTheDocument()
    })

    it('mostra "não lido" nos campos que decidem o casamento quando a extração não os trouxe', async () => {
        mockDetails({ d1: { ...invoiceDetail, extraction_result: { fields: {} } } })
        const dialog = await openCardDialog()
        const invoice = await within(dialog).findByRole('region', { name: 'Nota fiscal: nota.pdf' })
        // Valor da nota e CNPJ do fornecedor aparecem sempre, mesmo sem leitura.
        await waitFor(() => expect(within(invoice).getAllByText('não lido')).toHaveLength(2))
        expect(within(invoice).getByText('Valor da nota')).toBeInTheDocument()
    })

    it('esconde os campos opcionais não lidos e os revela sob demanda', async () => {
        const dialog = await openCardDialog()
        const invoice = await within(dialog).findByRole('region', { name: 'Nota fiscal: nota.pdf' })
        await within(invoice).findByText('Fornecedor Exemplo LTDA')
        // "Valor líquido" não veio na extração: fica escondido até o analista pedir.
        expect(within(invoice).queryByText('Valor líquido')).not.toBeInTheDocument()

        await userEvent.click(within(invoice).getByRole('button', { name: /Mostrar 2 campos não lidos/ }))
        expect(within(invoice).getByText('Valor líquido')).toBeInTheDocument()

        await userEvent.click(within(invoice).getByRole('button', { name: 'Ocultar campos não lidos' }))
        expect(within(invoice).queryByText('Valor líquido')).not.toBeInTheDocument()
    })

    it('se os dados de um documento não carregam, o outro continua visível', async () => {
        mockDetails({ d1: undefined })
        const dialog = await openCardDialog()
        const invoice = await within(dialog).findByRole('region', { name: 'Nota fiscal: nota.pdf' })
        expect(await within(invoice).findByText(/Não foi possível carregar os dados/)).toBeInTheDocument()
        const boleto = within(dialog).getByRole('region', { name: 'Boleto: boleto-1.pdf' })
        expect(await within(boleto).findByText('20/08/2026')).toBeInTheDocument()
    })

    it('cada painel tem "Corrigir dados", que abre a validação daquele documento', async () => {
        const navigate = renderPaymentsCapturingNavigation()
        const card = await screen.findByRole('article', { name: 'Processo de pagamento' })
        await userEvent.click(within(card).getByRole('button', { name: 'Ver documentos' }))
        const dialog = await screen.findByRole('dialog', { name: 'Documentos do processo' })
        const invoice = await within(dialog).findByRole('region', { name: 'Nota fiscal: nota.pdf' })
        const boleto = within(dialog).getByRole('region', { name: 'Boleto: boleto-1.pdf' })
        expect(within(invoice).getByRole('button', { name: /Corrigir dados/ })).toBeInTheDocument()

        await userEvent.click(within(boleto).getByRole('button', { name: /Corrigir dados/ }))

        // Vai para a Visão Geral (tela nova, não a /validation antiga) com o drawer do boleto
        // (não o da nota) e lembra de onde veio; o popup fecha.
        expect(navigate).toHaveBeenCalledTimes(1)
        expect(navigate).toHaveBeenCalledWith('/?validar=b1', { state: { from: '/payments' } })
        expect(screen.queryByRole('dialog', { name: 'Documentos do processo' })).not.toBeInTheDocument()
    })

    it('quem não pode validar documentos não vê "Corrigir dados"', async () => {
        mockMe(['inbox.view'])
        const dialog = await openCardDialog()
        await within(dialog).findByRole('region', { name: 'Nota fiscal: nota.pdf' })
        expect(within(dialog).queryByRole('button', { name: /Corrigir dados/ })).not.toBeInTheDocument()
    })

    it('busca os dados de novo ao reabrir, para mostrar o que foi corrigido na validação', async () => {
        const withValue = (value: string) => ({
            ...boletoDetail('b1', 'boleto-1.pdf', '2026-08-20'),
            extraction_result: { fields: { valor_boleto: field(value), data_vencimento: field('2026-08-20') } },
        })
        mockDetails({ b1: withValue('300,00') })
        const dialog = await openCardDialog()
        const boleto = await within(dialog).findByRole('region', { name: 'Boleto: boleto-1.pdf' })
        expect(await within(boleto).findByText(/R\$\s?300,00/)).toBeInTheDocument()
        await userEvent.click(screen.getByRole('button', { name: 'Fechar' }))

        mockDetails({ b1: withValue('310,00') }) // o analista corrigiu o valor
        await userEvent.click(within(screen.getByRole('article')).getByRole('button', { name: 'Ver documentos' }))

        const reopened = await screen.findByRole('dialog', { name: 'Documentos do processo' })
        const again = await within(reopened).findByRole('region', { name: 'Boleto: boleto-1.pdf' })
        expect(await within(again).findByText(/R\$\s?310,00/)).toBeInTheDocument()
    })

    it('abre o PDF ajustado à largura, para a página aparecer inteira', async () => {
        const dialog = await openCardDialog()
        const frame = await within(dialog).findByTitle('Documento nota.pdf')
        expect(frame).toHaveAttribute('src', expect.stringContaining('#view=FitH'))
        // A altura vem da largura do painel (página inteira), não de um valor fixo pequeno.
        const style = frame.getAttribute('style') ?? ''
        expect(style).toContain('cqw')
        expect(style).toContain('1.4143')
    })

    it('trava a rolagem do fundo enquanto o popup está aberto e a devolve ao fechar', async () => {
        await openCardDialog()
        expect(document.body.style.overflow).toBe('hidden')
        await userEvent.click(screen.getByRole('button', { name: 'Fechar' }))
        expect(document.body.style.overflow).not.toBe('hidden')
    })

    it('fecha pelo botão e pela tecla Escape', async () => {
        await openCardDialog()
        await userEvent.click(screen.getByRole('button', { name: 'Fechar' }))
        expect(screen.queryByRole('dialog', { name: 'Documentos do processo' })).not.toBeInTheDocument()

        await userEvent.click(within(screen.getByRole('article')).getByRole('button', { name: 'Ver documentos' }))
        await screen.findByRole('dialog', { name: 'Documentos do processo' })
        await userEvent.keyboard('{Escape}')
        expect(screen.queryByRole('dialog', { name: 'Documentos do processo' })).not.toBeInTheDocument()
    })

    it('o analista confirma o agrupamento sem sair do popup e o popup fecha', async () => {
        let confirmed = 0
        server.use(
            http.post(`${OCR}/payment-processes/p1/confirm`, () => {
                confirmed += 1
                return HttpResponse.json(
                    process({ status: 'CONFIRMED', decided_by: 'u', decided_at: '2026-11-10T11:00:00Z' }),
                )
            }),
        )
        const dialog = await openCardDialog()

        await userEvent.click(within(dialog).getByRole('button', { name: /Confirmar/ }))

        await waitFor(() => expect(confirmed).toBe(1))
        expect(screen.queryByRole('dialog', { name: 'Documentos do processo' })).not.toBeInTheDocument()
    })

    it('rejeitar pelo popup fecha o popup e pede a confirmação da rejeição', async () => {
        const dialog = await openCardDialog()
        await userEvent.click(within(dialog).getByRole('button', { name: /Rejeitar/ }))
        expect(screen.queryByRole('dialog', { name: 'Documentos do processo' })).not.toBeInTheDocument()
        expect(await screen.findByText('Rejeitar agrupamento?')).toBeInTheDocument()
    })

    it('quem só pode ver não tem botões de decisão no popup', async () => {
        mockMe(['inbox.view'])
        const dialog = await openCardDialog()
        expect(within(dialog).queryByRole('button', { name: /Confirmar/ })).not.toBeInTheDocument()
        expect(within(dialog).queryByRole('button', { name: /Rejeitar/ })).not.toBeInTheDocument()
    })

    it('um processo já confirmado também abre o popup, sem ações', async () => {
        server.use(
            http.get(`${OCR}/payment-processes`, () =>
                HttpResponse.json(
                    page([process({ status: 'CONFIRMED', decided_by: 'u', decided_at: '2026-11-10T11:00:00Z' })]),
                ),
            ),
        )
        const dialog = await openCardDialog()
        expect(within(dialog).queryByRole('button', { name: /Confirmar/ })).not.toBeInTheDocument()
    })
})

describe('Sem match: ver os documentos antes de montar o par', () => {
    beforeEach(() => {
        navigation.spy = null
        localStorage.setItem('access_token', 'tok')
        URL.createObjectURL = vi.fn(() => 'blob:preview')
        URL.revokeObjectURL = vi.fn()
        mockMe(['inbox.view', 'documents.validate'])
        server.use(
            http.get(`${OCR}/payment-candidates`, ({ request }) => {
                const results =
                    new URL(request.url).searchParams.get('kind') === 'invoice' ? [invoiceDoc()] : [boletoDoc()]
                return HttpResponse.json({ results, count: 1, page: 1, page_size: 10, total_pages: 1 })
            }),
        )
        mockDetails({
            nf1: { ...invoiceDetail, id: 'nf1', original_filename: 'nota-avulsa.pdf' },
            bol1: boletoDetail('bol1', 'boleto-avulso.pdf', '2026-09-05'),
        })
    })

    async function openUnmatched() {
        renderApp('/payments')
        await userEvent.click(await screen.findByRole('tab', { name: 'Sem match' }))
    }

    it('o botão de ver abre só aquele documento, sem conferência', async () => {
        await openUnmatched()
        await userEvent.click(await screen.findByRole('button', { name: 'Ver nota-avulsa.pdf' }))

        const dialog = await screen.findByRole('dialog', { name: 'Documentos do processo' })
        expect(within(dialog).getByRole('region', { name: 'Nota fiscal: nota-avulsa.pdf' })).toBeInTheDocument()
        expect(within(dialog).queryByRole('region', { name: /Boleto:/ })).not.toBeInTheDocument()
        expect(within(dialog).queryByRole('list', { name: 'Conferência' })).not.toBeInTheDocument()
        expect(within(dialog).queryByRole('button', { name: /Montar agrupamento/ })).not.toBeInTheDocument()
    })

    it('o popup de um documento só também tem "Corrigir dados"', async () => {
        const navigate = renderPaymentsCapturingNavigation()
        await userEvent.click(await screen.findByRole('tab', { name: 'Sem match' }))
        await userEvent.click(await screen.findByRole('button', { name: 'Ver boleto-avulso.pdf' }))
        const dialog = await screen.findByRole('dialog', { name: 'Documentos do processo' })

        await userEvent.click(await within(dialog).findByRole('button', { name: /Corrigir dados/ }))

        expect(navigate).toHaveBeenCalledWith('/?validar=bol1', { state: { from: '/payments' } })
    })

    it('ver um documento não o seleciona', async () => {
        await openUnmatched()
        await userEvent.click(await screen.findByRole('button', { name: 'Ver boleto-avulso.pdf' }))
        await userEvent.click(screen.getByRole('button', { name: 'Fechar' }))
        expect(screen.getByRole('checkbox', { name: 'Selecionar boleto-avulso.pdf' })).not.toBeChecked()
    })

    it('"Comparar lado a lado" só habilita com a nota e um boleto escolhidos', async () => {
        await openUnmatched()
        const compare = await screen.findByRole('button', { name: /Comparar lado a lado/ })
        expect(compare).toBeDisabled()
        await userEvent.click(await screen.findByLabelText('Selecionar nota-avulsa.pdf'))
        expect(compare).toBeDisabled()
        await userEvent.click(screen.getByLabelText('Selecionar boleto-avulso.pdf'))
        expect(compare).toBeEnabled()
    })

    it('compara a seleção e monta o agrupamento pelo popup', async () => {
        let body: unknown = null
        server.use(
            http.post(`${OCR}/payment-processes/manual`, async ({ request }) => {
                body = await request.json()
                return HttpResponse.json(process({ origin: 'MANUAL' }), { status: 201 })
            }),
        )
        await openUnmatched()
        await userEvent.click(await screen.findByLabelText('Selecionar nota-avulsa.pdf'))
        await userEvent.click(screen.getByLabelText('Selecionar boleto-avulso.pdf'))
        await userEvent.click(screen.getByRole('button', { name: /Comparar lado a lado/ }))

        const dialog = await screen.findByRole('dialog', { name: 'Documentos do processo' })
        expect(within(dialog).getByRole('region', { name: 'Nota fiscal: nota-avulsa.pdf' })).toBeInTheDocument()
        expect(within(dialog).getByRole('region', { name: 'Boleto: boleto-avulso.pdf' })).toBeInTheDocument()
        expect(await within(dialog).findByRole('list', { name: 'Conferência' })).toBeInTheDocument()

        await userEvent.click(within(dialog).getByRole('button', { name: /Montar agrupamento/ }))

        await waitFor(() => expect(body).toEqual({ invoice_id: 'nf1', boleto_ids: ['bol1'] }))
        expect(screen.queryByRole('dialog', { name: 'Documentos do processo' })).not.toBeInTheDocument()
    })

    it('se montar o par falha, o popup fecha e o erro aparece na barra de seleção', async () => {
        server.use(
            http.post(`${OCR}/payment-processes/manual`, () =>
                HttpResponse.json(
                    { detail: 'Este boleto já está em outro agrupamento.', code: 'boleto_taken' },
                    { status: 409 },
                ),
            ),
        )
        await openUnmatched()
        await userEvent.click(await screen.findByLabelText('Selecionar nota-avulsa.pdf'))
        await userEvent.click(screen.getByLabelText('Selecionar boleto-avulso.pdf'))
        await userEvent.click(screen.getByRole('button', { name: /Comparar lado a lado/ }))
        const dialog = await screen.findByRole('dialog', { name: 'Documentos do processo' })

        await userEvent.click(within(dialog).getByRole('button', { name: /Montar agrupamento/ }))

        expect(await screen.findByText('Este boleto já está em outro agrupamento.')).toBeInTheDocument()
        expect(screen.queryByRole('dialog', { name: 'Documentos do processo' })).not.toBeInTheDocument()
    })
})
