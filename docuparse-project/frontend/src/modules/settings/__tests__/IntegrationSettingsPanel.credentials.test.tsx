import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../../__tests__/mocks/server'
import { IntegrationSettingsPanel } from '../components/IntegrationSettingsPanel'
import { renderSettingsPanel } from './renderSettingsPanel'

const URL = '/api/ocr/settings/integrations'

function mockSettings(configured: boolean) {
    const saved: unknown[] = []
    server.use(
        http.get(URL, () => HttpResponse.json({ superlogica_credentials_configured: configured })),
        http.patch(URL, async ({ request }) => {
            saved.push(await request.json())
            return HttpResponse.json({ superlogica_credentials_configured: true, administrator_cnpj: '11222333000181' })
        }),
    )
    return saved
}

describe('IntegrationSettingsPanel - credenciais do Superlógica', () => {
    it('só envia os tokens quando informados e nunca os exibe depois de salvar', async () => {
        const saved = mockSettings(false)
        renderSettingsPanel(<IntegrationSettingsPanel />)
        await screen.findByText('Salvar integracoes')

        await userEvent.type(screen.getByLabelText(/Token do app/), 'APP-SECRET')
        await userEvent.type(screen.getByLabelText(/Token de acesso/), 'ACCESS-SECRET')
        await userEvent.type(screen.getByLabelText('CNPJ da administradora'), '11222333000181')
        await userEvent.click(screen.getByText('Salvar integracoes'))

        await screen.findByText('Configuracoes de integracao salvas.')
        expect(saved[0]).toMatchObject({
            superlogica_app_token: 'APP-SECRET',
            superlogica_access_token: 'ACCESS-SECRET',
            administrator_cnpj: '11222333000181',
        })
        expect(screen.getByLabelText(/Token do app/)).toHaveValue('')
        expect(screen.getByLabelText(/Token do app/)).toHaveAttribute(
            'placeholder',
            'Configurado (informe para trocar)',
        )
    })

    it('não reenvia os tokens quando o analista não os digita', async () => {
        const saved = mockSettings(true)
        renderSettingsPanel(<IntegrationSettingsPanel />)
        await screen.findByText('Salvar integracoes')
        await userEvent.click(screen.getByText('Salvar integracoes'))
        await screen.findByText('Configuracoes de integracao salvas.')
        expect(saved[0]).not.toHaveProperty('superlogica_app_token')
        expect(saved[0]).not.toHaveProperty('superlogica_access_token')
    })

    it('recusa salvar com só um dos tokens', async () => {
        const saved = mockSettings(false)
        renderSettingsPanel(<IntegrationSettingsPanel />)
        await screen.findByText('Salvar integracoes')
        await userEvent.type(screen.getByLabelText(/Token do app/), 'so-um')
        await userEvent.click(screen.getByText('Salvar integracoes'))
        expect(await screen.findByText('Informe os dois tokens do Superlogica juntos.')).toBeInTheDocument()
        expect(saved).toHaveLength(0)
    })

    it('testa a conexão e mostra o motivo quando falha', async () => {
        mockSettings(true)
        server.use(
            http.post('/api/ocr/import/test-connection', () =>
                HttpResponse.json({ ok: false, detail: 'O Superlógica recusou as credenciais (HTTP 401).' }),
            ),
        )
        renderSettingsPanel(<IntegrationSettingsPanel />)
        const button = await screen.findByRole('button', { name: 'Testar conexao' })
        await waitFor(() => expect(button).toBeEnabled())
        await userEvent.click(button)
        expect(await screen.findByText(/recusou as credenciais \(HTTP 401\)/)).toBeInTheDocument()
    })
})
