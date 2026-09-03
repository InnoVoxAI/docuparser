import { Alert } from '../../../shared/components'
import { STAGE_LABELS, STATUS_GROUP_LABELS, STATUS_GROUP_ORDER } from '../types'
import type { ProcessStats } from '../types'
import { StatBreakdown } from './StatBreakdown'
import type { StatRow } from './StatBreakdown'

const STATUS_BAR_CLASS: Record<string, string> = {
    em_fila: 'bg-zinc-400',
    aguardando_validacao: 'bg-amber-400',
    aguardando_classificacao: 'bg-sky-400',
    erro: 'bg-red-400',
}

const STAGE_ORDER = ['register', 'ocr', 'extraction', 'validation_decision', 'classification']

function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms} ms`
    return `${(ms / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} s`
}

function StatCard({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
    return (
        <div className="rounded-lg border border-zinc-200 bg-white p-4">
            <div className={`text-2xl font-semibold tabular-nums ${tone ?? 'text-zinc-900'}`}>{value}</div>
            <div className="mt-1 text-xs font-medium text-zinc-500">{label}</div>
        </div>
    )
}

function toRows(entries: Record<string, number>): StatRow[] {
    return Object.entries(entries)
        .filter(([, value]) => value > 0)
        .sort((a, b) => b[1] - a[1])
        .map(([label, value]) => ({ label, value }))
}

export function ProcessStatsView({ stats }: { stats: ProcessStats }) {
    const statusRows: StatRow[] = STATUS_GROUP_ORDER.map((group) => ({
        label: STATUS_GROUP_LABELS[group],
        value: stats.by_status[group] ?? 0,
        barClass: STATUS_BAR_CLASS[group],
    }))

    const stageRows: StatRow[] = STAGE_ORDER.filter((key) => (stats.by_stage[key] ?? 0) > 0).map((key) => ({
        label: STAGE_LABELS[key] ?? key,
        value: stats.by_stage[key] ?? 0,
    }))

    const durationRows = toRows(stats.avg_duration_ms)

    return (
        <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatCard label="Processos no total" value={stats.total} />
                <StatCard
                    label="Aguardando validação"
                    value={stats.by_status.aguardando_validacao}
                    tone="text-amber-600"
                />
                <StatCard
                    label="Aguardando classificação"
                    value={stats.by_status.aguardando_classificacao}
                    tone="text-sky-600"
                />
                <StatCard
                    label="Com erro"
                    value={stats.errors.documents_with_error}
                    tone={stats.errors.documents_with_error > 0 ? 'text-red-600' : undefined}
                />
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
                <StatBreakdown title="Por status" rows={statusRows} total={stats.total} />
                <StatBreakdown title="Por etapa do processo" rows={stageRows} total={stats.total} />
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
                <StatBreakdown
                    title="Erros por etapa"
                    rows={toRows(stats.errors.by_step).map((row) => ({ ...row, barClass: 'bg-red-400' }))}
                    emptyText="Nenhum erro registrado."
                />
                <StatBreakdown
                    title="Erros por tipo"
                    rows={toRows(stats.errors.by_type).map((row) => ({ ...row, barClass: 'bg-red-400' }))}
                    emptyText="Nenhum erro registrado."
                />
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
                <section className="rounded-lg border border-zinc-200 bg-white p-4">
                    <h2 className="text-sm font-semibold text-zinc-800">Resultado da validação</h2>
                    <div className="mt-3 grid grid-cols-2 gap-3">
                        <StatCard label="Aprovados" value={stats.validation.approved} tone="text-emerald-600" />
                        <StatCard label="Rejeitados" value={stats.validation.rejected} tone="text-red-600" />
                    </div>
                    <p className="mt-3 text-xs text-zinc-500">
                        Retentativas manuais de processamento: {stats.manual_retries}
                    </p>
                </section>

                <section className="rounded-lg border border-zinc-200 bg-white p-4">
                    <h2 className="text-sm font-semibold text-zinc-800">Volume de entrada</h2>
                    <div className="mt-3 grid grid-cols-3 gap-3">
                        <StatCard label="Últimas 24h" value={stats.volume.last_24h} />
                        <StatCard label="Últimos 7 dias" value={stats.volume.last_7d} />
                        <StatCard label="Últimos 30 dias" value={stats.volume.last_30d} />
                    </div>
                </section>
            </div>

            {durationRows.length > 0 ? (
                <StatBreakdown
                    title="Tempo médio por etapa"
                    rows={durationRows.map((row) => ({
                        ...row,
                        // exibe o tempo formatado, mantendo a barra proporcional ao valor bruto
                        label: `${row.label} — ${formatDuration(row.value)}`,
                        barClass: 'bg-sky-400',
                    }))}
                />
            ) : (
                <Alert>Ainda não há execuções concluídas o suficiente para calcular tempos médios.</Alert>
            )}
        </div>
    )
}
