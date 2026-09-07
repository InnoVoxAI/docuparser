import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ProcessStatusBadge } from '../components/ProcessStatusBadge'

describe('ProcessStatusBadge', () => {
    it('mostra um círculo colorido diferente por status', () => {
        const cases: { label: string; dotColor: string }[] = [
            { label: 'Erro', dotColor: 'bg-red-500' },
            { label: 'Aguardando validação', dotColor: 'bg-amber-500' },
            { label: 'Aguardando classificação', dotColor: 'bg-sky-500' },
            { label: 'Em Fila', dotColor: 'bg-zinc-400' },
        ]

        for (const { label, dotColor } of cases) {
            const { container, unmount } = render(<ProcessStatusBadge label={label} />)
            expect(screen.getByText(label)).toBeInTheDocument()
            const dot = container.querySelector('.rounded-full')
            expect(dot).toHaveClass(dotColor)
            unmount()
        }
    })

    it('cai num círculo neutro pra um rótulo desconhecido', () => {
        const { container } = render(<ProcessStatusBadge label="Desconhecido" />)
        expect(container.querySelector('.rounded-full')).toHaveClass('bg-zinc-400')
    })
})
