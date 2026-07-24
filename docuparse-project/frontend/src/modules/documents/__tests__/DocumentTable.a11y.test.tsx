import { render, screen } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it, vi } from 'vitest'
import { DocumentTable } from '../components/DocumentTable'
import type { Document } from '../types'

// SC-006 — DocumentTable é a peça de UI mais reutilizada do módulo `documents`
// (Dashboard/Inbox), incluindo o caminho `selectable` (checkboxes de seleção
// em massa) e o modo `compact`.

function doc(overrides: Partial<Document> = {}): Document {
    return {
        id: 'd1',
        status: 'RECEIVED',
        channel: 'manual',
        original_filename: 'documento.pdf',
        content_type: 'application/pdf',
        extraction_result: null,
        active_field_version_number: null,
        ...overrides,
    }
}

describe('DocumentTable - acessibilidade (SC-006)', () => {
    it('não tem violações de acessibilidade com documentos listados', async () => {
        const { container } = render(
            <DocumentTable
                documents={[
                    doc({ id: 'd1', original_filename: 'nota-fiscal.pdf' }),
                    doc({ id: 'd2', original_filename: 'boleto.pdf', status: 'APPROVED' }),
                ]}
                onSelectDocument={vi.fn()}
            />,
        )
        await screen.findByText('nota-fiscal.pdf')
        expect(await axe(container)).toHaveNoViolations()
    })

    it('não tem violações de acessibilidade no estado vazio', async () => {
        const { container } = render(<DocumentTable documents={[]} onSelectDocument={vi.fn()} />)
        await screen.findByText('Nenhum documento encontrado.')
        expect(await axe(container)).toHaveNoViolations()
    })

    it('não tem violações de acessibilidade com seleção em massa habilitada', async () => {
        const { container } = render(
            <DocumentTable
                documents={[doc({ id: 'd1' })]}
                onSelectDocument={vi.fn()}
                selectable
                bulkSelectedIds={new Set()}
                onBulkSelectionChange={vi.fn()}
            />,
        )
        await screen.findByText('documento.pdf')
        expect(await axe(container)).toHaveNoViolations()
    })
})
