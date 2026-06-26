import { describe, it, expect, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'
import { renderApp } from './utils'

// US1 / T016 — visibilidade de navegação conforme as permissões do usuário.
function mockMe(permissions: string[]) {
  server.use(
    http.get('/api/auth/me', () =>
      HttpResponse.json({ id: 'u1', name: 'User', email: 'u@docuparse.local', permissions }),
    ),
  )
}

describe('Permissões e navegação', () => {
  beforeEach(() => localStorage.setItem('access_token', 'tok'))

  it('exibe apenas itens permitidos (somente inbox.view)', async () => {
    mockMe(['inbox.view'])
    renderApp()
    expect((await screen.findAllByText('Inbox')).length).toBeGreaterThan(0)
    expect(screen.queryAllByText('Dashboard').length).toBeGreaterThan(0)
    // Sem documents.validate / roles.manage / users.manage:
    expect(screen.queryAllByText('Validacao')).toHaveLength(0)
    expect(screen.queryAllByText('Configuracoes')).toHaveLength(0)
    expect(screen.queryAllByText('Usuários')).toHaveLength(0)
  })

  it('exibe "Validacao" quando o usuário tem documents.validate', async () => {
    mockMe(['inbox.view', 'documents.validate'])
    renderApp()
    expect((await screen.findAllByText('Validacao')).length).toBeGreaterThan(0)
  })

  it('exibe itens administrativos quando o usuário tem as permissões', async () => {
    mockMe(['inbox.view', 'roles.manage', 'users.manage'])
    renderApp()
    expect((await screen.findAllByText('Roles')).length).toBeGreaterThan(0)
    expect(screen.queryAllByText('Usuários').length).toBeGreaterThan(0)
  })
})
