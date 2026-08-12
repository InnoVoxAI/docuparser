import { render } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it, vi } from 'vitest'
import { WhatsAppSettingsPanel } from '../components/WhatsAppSettingsPanel'

// Smoke apenas — painel puramente estático/apresentacional (decisão #2 do
// handoff de T036-T040, sem schema Zod nem estado de formulário real).

describe('WhatsAppSettingsPanel - acessibilidade (smoke)', () => {
    it('não tem violações de acessibilidade', async () => {
        const { container } = render(<WhatsAppSettingsPanel onPoll={vi.fn()} />)
        expect(await axe(container)).toHaveNoViolations()
    })
})
