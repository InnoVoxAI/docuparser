import { screen } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../../__tests__/mocks/server'
import { OcrSettingsPanel } from '../components/OcrSettingsPanel'
import { renderSettingsPanel } from './renderSettingsPanel'

// SC-006 — primeiro painel de Configurações migrado para RHF+Zod (T037).

describe('OcrSettingsPanel - acessibilidade (SC-006)', () => {
    it('não tem violações de acessibilidade', async () => {
        server.use(http.get('/api/ocr/settings/ocr', () => HttpResponse.json({})))
        const { container } = renderSettingsPanel(<OcrSettingsPanel />)
        await screen.findByText('Salvar OCR')
        expect(await axe(container)).toHaveNoViolations()
    })
})
