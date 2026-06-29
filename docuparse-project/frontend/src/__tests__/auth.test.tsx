import { describe, it, expect, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from './utils'

// US1 / T017 — integração de autenticação (login persiste tokens, /me restaura, etc.)
describe('Autenticação', () => {
  beforeEach(() => localStorage.clear())

  it('mostra a tela de login quando não há sessão', async () => {
    renderApp()
    expect(await screen.findByText('Entre com sua conta para continuar')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument()
  })

  it('restaura a sessão quando há token (via /me) e entra na aplicação', async () => {
    localStorage.setItem('access_token', 'tok')
    renderApp()
    expect((await screen.findAllByText('Inbox')).length).toBeGreaterThan(0)
  })

  it('faz login pelo formulário, persiste tokens e entra na aplicação', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.type(await screen.findByPlaceholderText('voce@empresa.com'), 'op@docuparse.local')
    await user.type(screen.getByPlaceholderText('••••••••'), 'secret')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect((await screen.findAllByText('Inbox')).length).toBeGreaterThan(0)
    expect(localStorage.getItem('access_token')).toBe('test-access')
    expect(localStorage.getItem('refresh_token')).toBe('test-refresh')
  })
})
