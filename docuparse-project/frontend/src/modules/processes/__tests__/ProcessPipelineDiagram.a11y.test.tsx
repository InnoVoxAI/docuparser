import { render, screen } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it, vi } from 'vitest'
import { ProcessPipelineDiagram } from '../components/ProcessPipelineDiagram'
import type { ProcessStep } from '../types'

function steps(overrides: Partial<ProcessStep>[] = []): ProcessStep[] {
    const base: ProcessStep[] = [
        { key: 'register', label: 'Registro', status: 'OK', retryable: false, executions: [] },
        { key: 'ocr', label: 'OCR', status: 'PENDING', retryable: true, executions: [] },
        { key: 'extraction', label: 'Extração', status: 'PENDING', retryable: true, executions: [] },
        { key: 'validation_decision', label: 'Validação', status: 'PENDING', retryable: false, executions: [] },
    ]
    return base.map((step, index) => ({ ...step, ...overrides[index] }))
}

describe('ProcessPipelineDiagram - acessibilidade', () => {
    it('não tem violações de acessibilidade num pipeline pendente', async () => {
        const { container } = render(
            <ProcessPipelineDiagram steps={steps()} selectedStepKey={null} onSelectStep={vi.fn()} />,
        )
        await screen.findByText('Registro')
        expect(await axe(container)).toHaveNoViolations()
    })

    it('não tem violações de acessibilidade com uma etapa em erro selecionada', async () => {
        const { container } = render(
            <ProcessPipelineDiagram
                steps={steps([{}, { status: 'ERROR' }])}
                selectedStepKey="ocr"
                onSelectStep={vi.fn()}
            />,
        )
        await screen.findByText('Falhou')
        expect(await axe(container)).toHaveNoViolations()
    })
})
