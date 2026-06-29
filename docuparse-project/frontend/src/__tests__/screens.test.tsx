import { describe, it, expect, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
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
]

describe('Telas / navegação (smoke)', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'tok')
    server.use(
      http.get('/api/auth/me', () =>
        HttpResponse.json({ id: 'u1', name: 'Admin', email: 'admin@docuparse.local', permissions: ALL_PERMISSIONS }),
      ),
    )
  })

  it('renderiza todos os itens de navegação para um usuário com todas as permissões', async () => {
    renderApp()
    for (const label of ['Upload', 'Inbox', 'Dashboard', 'Validacao', 'Operacoes', 'Configuracoes', 'Usuários', 'Roles']) {
      expect((await screen.findAllByText(label)).length).toBeGreaterThan(0)
    }
  })
})
