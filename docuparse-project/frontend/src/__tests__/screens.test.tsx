import { describe, it, expect, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
import { renderApp } from './utils'

// US1 / T015 — smoke das telas: com todas as permissões, todos os itens de
// navegação (telas) estão registrados e a aplicação monta sem erros.
const ALL_PERMISSIONS = [
    'documents.send',
    'inbox.view',
    'documents.validate',
    'operations.access',
    'roles.manage',
    'users.manage',
    'models.edit',
]

describe('Telas / navegação (smoke)', () => {
    beforeEach(() => {
        localStorage.setItem('access_token', 'tok')
        server.use(
            http.get('/api/auth/me', () =>
                HttpResponse.json({
                    id: 'u1',
                    name: 'Admin',
                    email: 'admin@docuparse.local',
                    permissions: ALL_PERMISSIONS,
                }),
            ),
        )
    })

    it('renderiza todos os itens de navegação para um usuário com todas as permissões', async () => {
        // A sidebar (com todos os NAV_ITEMS) só aparece nas rotas com layout
        // completo — as telas de processos (`/`, `/stats`) rodam sem ela.
        renderApp('/dashboard')
        for (const label of [
            'Upload',
            'Inbox',
            'Dashboard',
            'Validação',
            'Operações',
            'Configurações',
            'Usuários',
            'Roles',
        ]) {
            expect((await screen.findAllByText(label)).length).toBeGreaterThan(0)
        }
    })

    // 4c/T025 — navegação por rotas reais (FR-002): clicar num item de menu
    // muda a URL de fato (React Router), não só um estado interno de view.
    it('navega por rotas reais ao clicar nos itens de menu', async () => {
        const user = userEvent.setup()
        renderApp('/dashboard')
        await user.click((await screen.findAllByText('Inbox'))[0])
        expect(window.location.pathname).toBe('/inbox')
        await user.click((await screen.findAllByText('Dashboard'))[0])
        expect(window.location.pathname).toBe('/dashboard')
    })
})
