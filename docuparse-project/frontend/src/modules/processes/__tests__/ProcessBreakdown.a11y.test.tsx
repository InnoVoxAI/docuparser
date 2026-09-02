import { render, screen } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it, vi } from 'vitest'
import { ProcessBreakdown } from '../components/ProcessBreakdown'
import type { ProcessPipeline, ProcessStep, StepStatus } from '../types'

function pipeline(statuses: Partial<Record<ProcessStep['key'], StepStatus>> = {}): ProcessPipeline {
    const base: ProcessStep[] = [
        { key: 'register', label: 'Registro', status: 'OK', retryable: false, executions: [] },
        { key: 'ocr', label: 'OCR', status: 'PENDING', retryable: true, executions: [] },
        { key: 'extraction', label: 'Extração', status: 'PENDING', retryable: true, executions: [] },
        { key: 'validation_decision', label: 'Validação', status: 'PENDING', retryable: false, executions: [] },
        { key: 'classification', label: 'Classificação', status: 'PENDING', retryable: false, executions: [] },
    ]
    return {
        document_id: 'd1',
        original_filename: 'doc.pdf',
        steps: base.map((step) => ({ ...step, status: statuses[step.key] ?? step.status })),
    }
}

describe('ProcessBreakdown - acessibilidade', () => {
    it('não tem violações num processo ainda na fila', async () => {
        const { container } = render(
            <ProcessBreakdown pipeline={pipeline()} onOpenLogs={vi.fn()} onOpenValidation={vi.fn()} />,
        )
        await screen.findByText('Em fila')
        expect(await axe(container)).toHaveNoViolations()
    })

    it('expõe "Ingestão" como botão quando há erro e chama onOpenLogs', async () => {
        const onOpenLogs = vi.fn()
        const { container } = render(
            <ProcessBreakdown
                pipeline={pipeline({ ocr: 'ERROR' })}
                onOpenLogs={onOpenLogs}
                onOpenValidation={vi.fn()}
            />,
        )
        const button = await screen.findByRole('button', { name: /Ingestão/ })
        button.click()
        expect(onOpenLogs).toHaveBeenCalled()
        expect(await axe(container)).toHaveNoViolations()
    })

    it('expõe "Validação" como botão quando aguarda decisão humana', async () => {
        const onOpenValidation = vi.fn()
        render(
            <ProcessBreakdown
                pipeline={pipeline({ ocr: 'OK', extraction: 'OK' })}
                onOpenLogs={vi.fn()}
                onOpenValidation={onOpenValidation}
            />,
        )
        const button = await screen.findByRole('button', { name: /Validação/ })
        button.click()
        expect(onOpenValidation).toHaveBeenCalled()
    })
})
