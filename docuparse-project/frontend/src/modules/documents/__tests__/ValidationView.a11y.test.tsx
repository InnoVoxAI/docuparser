import { screen } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it, vi } from 'vitest'
import { renderWithQueryClient } from '../../../__tests__/utils'
import { ValidationView } from '../components/ValidationView'
import type { Document } from '../types'

// SC-006 — cobre tanto o estado "sem documento selecionado" quanto o formulário
// de validação completo (campos extraídos, notas, ações de aprovar/rejeitar).

const baseDoc: Document = {
    id: 'doc-1',
    status: 'EXTRACTION_COMPLETED',
    channel: 'manual',
    original_filename: 'nota.pdf',
    content_type: 'application/pdf',
    active_field_version_number: 1,
    extraction_result: {
        schema_id: 's',
        schema_version: 'v1',
        fields: { valor: { value: '100', confidence: 0.8 } },
        confidence: 0.8,
        requires_human_validation: true,
    },
}

describe('ValidationView - acessibilidade (SC-006)', () => {
    it('não tem violações de acessibilidade sem documento selecionado', async () => {
        const { container } = renderWithQueryClient(
            <ValidationView
                schemas={[]}
                selectedDocument={null}
                selectedDocumentId=""
                onValidated={vi.fn()}
                onBackToInbox={vi.fn()}
            />,
        )
        await screen.findByText(/Selecione um documento no Inbox/i)
        expect(await axe(container)).toHaveNoViolations()
    })

    it('não tem violações de acessibilidade com o formulário de validação preenchido', async () => {
        const { container } = renderWithQueryClient(
            <ValidationView
                schemas={[]}
                selectedDocument={baseDoc}
                selectedDocumentId={baseDoc.id}
                onValidated={vi.fn()}
                onBackToInbox={vi.fn()}
            />,
        )
        await screen.findByDisplayValue('100')
        expect(await axe(container)).toHaveNoViolations()
    })
})
