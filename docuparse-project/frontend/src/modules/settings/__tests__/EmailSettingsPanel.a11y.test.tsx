import { screen } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../../__tests__/mocks/server'
import { EmailSettingsPanel } from '../components/EmailSettingsPanel'
import { renderSettingsPanel } from './renderSettingsPanel'

describe('EmailSettingsPanel - acessibilidade (SC-006)', () => {
    it('não tem violações de acessibilidade', async () => {
        server.use(http.get('/api/ocr/settings/email', () => HttpResponse.json({})))
        const { container } = renderSettingsPanel(<EmailSettingsPanel />)
        await screen.findByText('Salvar email')
        expect(await axe(container)).toHaveNoViolations()
    })
})
