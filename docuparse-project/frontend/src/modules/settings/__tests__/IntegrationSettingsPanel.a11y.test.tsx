import { screen } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../../__tests__/mocks/server'
import { IntegrationSettingsPanel } from '../components/IntegrationSettingsPanel'
import { renderSettingsPanel } from './renderSettingsPanel'

describe('IntegrationSettingsPanel - acessibilidade (SC-006)', () => {
    it('não tem violações de acessibilidade', async () => {
        server.use(http.get('/api/ocr/settings/integrations', () => HttpResponse.json({})))
        const { container } = renderSettingsPanel(<IntegrationSettingsPanel />)
        await screen.findByText('Salvar integracoes')
        expect(await axe(container)).toHaveNoViolations()
    })
})
