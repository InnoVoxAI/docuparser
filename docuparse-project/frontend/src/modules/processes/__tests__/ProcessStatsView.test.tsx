import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ProcessStatsView } from '../components/ProcessStatsView'
import type { ProcessStats } from '../types'

const stats: ProcessStats = {
    total: 20,
    by_status: { em_fila: 8, aguardando_validacao: 5, aguardando_classificacao: 4, erro: 3 },
    by_stage: { register: 8, ocr: 2, extraction: 1, validation_decision: 5, classification: 4 },
    errors: {
        documents_with_error: 3,
        by_step: { 'Ingestão (OCR)': 2, 'Ingestão (extração)': 1 },
        by_type: { RuntimeError: 2, TimeoutError: 1 },
    },
    validation: { approved: 6, rejected: 2 },
    volume: { last_24h: 4, last_7d: 12, last_30d: 20 },
    avg_duration_ms: { 'Ingestão (OCR)': 3400, 'Ingestão (extração)': 42000 },
    manual_retries: 1,
}

describe('ProcessStatsView', () => {
    it('mostra os números agregados principais', () => {
        render(<ProcessStatsView stats={stats} />)

        expect(screen.getByText('Processos no total')).toBeInTheDocument()
        // cartão "com erro"
        expect(screen.getByText('Com erro')).toBeInTheDocument()
        // seções de breakdown
        expect(screen.getByText('Por status')).toBeInTheDocument()
        expect(screen.getByText('Por etapa do processo')).toBeInTheDocument()
        expect(screen.getByText('Erros por tipo')).toBeInTheDocument()
        expect(screen.getByText('RuntimeError')).toBeInTheDocument()
        // volume
        expect(screen.getByText('Últimas 24h')).toBeInTheDocument()
        // tempo médio formatado (42000ms -> "42 s")
        expect(screen.getByText(/Ingestão \(extração\) — 42 s/)).toBeInTheDocument()
    })

    it('lida com base vazia sem quebrar', () => {
        const empty: ProcessStats = {
            total: 0,
            by_status: { em_fila: 0, aguardando_validacao: 0, aguardando_classificacao: 0, erro: 0 },
            by_stage: {},
            errors: { documents_with_error: 0, by_step: {}, by_type: {} },
            validation: { approved: 0, rejected: 0 },
            volume: { last_24h: 0, last_7d: 0, last_30d: 0 },
            avg_duration_ms: {},
            manual_retries: 0,
        }
        render(<ProcessStatsView stats={empty} />)
        expect(screen.getAllByText('Nenhum erro registrado.').length).toBeGreaterThan(0)
        expect(screen.getByText(/não há execuções concluídas o suficiente/i)).toBeInTheDocument()
    })
})
