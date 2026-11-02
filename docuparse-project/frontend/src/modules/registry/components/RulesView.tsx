import { useEffect, useMemo, useState } from 'react'
import { Plus } from 'lucide-react'
import { Alert, ConfirmDialog, EmptyState } from '../../../shared/components'
import { useAuth } from '../../auth'
import { useChartAccounts, useCharts, useCondominiums } from '../hooks'
import { useRules } from '../hooks/useRules'
import { RULES_PAGE_SIZE, type Rule, type RuleFilters } from '../schemas/rules'
import { describeRuleSupplier } from '../rules'
import { ReviewPager } from './ReviewPager'
import { RuleFormDialog, type RuleFormValues } from './RuleFormDialog'
import { RulesFilters } from './RulesFilters'
import { RulesTable } from './RulesTable'
import { ListChecks } from 'lucide-react'

const NO_FILTERS: RuleFilters = { search: '', origin: '', prefills: '', offset: 0 }
const SEARCH_DELAY_MS = 300

/** Regras de fornecedor: que conta cada fornecedor recebe, de onde veio a regra e se ela pré-preenche. */
export function RulesView() {
    const { hasPermission } = useAuth()
    const canEdit = hasPermission('models.edit')
    const charts = useCharts()
    const condominiums = useCondominiums()
    const [chosenChart, setChosenChart] = useState('')
    const [filters, setFilters] = useState<RuleFilters>(NO_FILTERS)
    const [search, setSearch] = useState('')
    const [form, setForm] = useState<Rule | 'new' | null>(null)
    const [deleting, setDeleting] = useState<Rule | null>(null)
    const [notice, setNotice] = useState('')

    // O plano com mais condomínios é o que o analista quase sempre quer ver.
    const defaultChart = useMemo(() => {
        const counts = new Map<string, number>()
        condominiums.data?.forEach(
            (c) =>
                c.chart_of_accounts_id &&
                counts.set(c.chart_of_accounts_id, (counts.get(c.chart_of_accounts_id) ?? 0) + 1),
        )
        const active = (charts.data ?? []).filter((c) => c.is_active)
        return active.sort((a, b) => (counts.get(b.id) ?? 0) - (counts.get(a.id) ?? 0))[0]?.id ?? ''
    }, [charts.data, condominiums.data])
    const chartId = chosenChart || defaultChart

    useEffect(() => {
        const timer = setTimeout(() => setFilters((f) => ({ ...f, search: search.trim(), offset: 0 })), SEARCH_DELAY_MS)
        return () => clearTimeout(timer)
    }, [search])

    const accounts = useChartAccounts(chartId || null)
    const rules = useRules(chartId || null, filters)
    const results = rules.page?.results ?? []
    const total = rules.page?.count ?? 0
    const filtered = filters.search !== '' || filters.origin !== '' || filters.prefills !== ''

    const openForm = (target: Rule | 'new') => {
        setNotice('')
        setForm(target)
    }
    const close = () => {
        setForm(null)
        rules.resetErrors()
    }
    const submit = (values: RuleFormValues) => {
        const done = {
            onSuccess: () => {
                close()
                setNotice('Regra salva. Vale para os documentos novos deste plano.')
            },
        }
        if (form && form !== 'new') {
            rules.update.mutate({ ruleId: form.id, patch: { ledger_account_id: values.ledger_account_id } }, done)
        } else {
            rules.create.mutate(
                {
                    supplier_tax_id: values.mode === 'tax' ? values.supplier : '',
                    keyword: values.keyword,
                    ledger_account_id: values.ledger_account_id,
                },
                done,
            )
        }
    }
    const toggle = (rule: Rule) => {
        setNotice('')
        rules.update.mutate(
            { ruleId: rule.id, patch: { is_active: !rule.is_active } },
            { onSuccess: () => setNotice(rule.is_active ? 'Regra desativada.' : 'Regra ativada.') },
        )
    }

    return (
        <div className="space-y-4 p-4">
            <div className="space-y-1 md:pr-16">
                <h1 className="text-lg font-semibold text-zinc-900">Regras de fornecedor</h1>
                <p className="text-sm text-zinc-600">
                    Dizem em que conta cai cada fornecedor. As do histórico do ERP só pré-preenchem com 3 ou mais
                    lançamentos e 90% de concordância. Editar, desativar ou criar uma regra a torna manual: a
                    atualização do histórico não a altera.
                </p>
            </div>
            {charts.error ? <Alert tone="error">Nao foi possivel carregar os planos de contas.</Alert> : null}
            {(charts.data?.length ?? 0) > 0 ? (
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <RulesFilters
                        charts={charts.data ?? []}
                        chartId={chartId}
                        filters={filters}
                        search={search}
                        onChart={(id) => {
                            setChosenChart(id)
                            setFilters(NO_FILTERS)
                            setSearch('')
                        }}
                        onSearch={setSearch}
                        onFilter={(patch) => setFilters((f) => ({ ...f, ...patch, offset: 0 }))}
                    />
                    {canEdit ? (
                        <button
                            type="button"
                            onClick={() => openForm('new')}
                            className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                        >
                            <Plus size={16} aria-hidden="true" /> Nova regra
                        </button>
                    ) : null}
                </div>
            ) : null}
            {notice ? (
                <Alert tone="success" className="">
                    {notice}
                </Alert>
            ) : null}
            {rules.loadError ? (
                <Alert tone="error" className="">
                    {rules.loadError}
                </Alert>
            ) : null}
            {!form && !deleting && rules.actionError ? (
                <Alert tone="error" className="">
                    {rules.actionError}
                </Alert>
            ) : null}
            {rules.loading ? <p className="text-sm text-zinc-500">Carregando regras...</p> : null}
            {charts.data?.length === 0 ? (
                <EmptyState icon={ListChecks} text="Importe um plano de contas em Cadastros para criar regras." />
            ) : null}
            {!rules.loading && chartId && results.length === 0 && !rules.loadError ? (
                <EmptyState
                    icon={ListChecks}
                    text={
                        filtered
                            ? 'Nenhuma regra com estes filtros.'
                            : 'Nenhuma regra neste plano ainda. Elas vêm do histórico do ERP (a cada sincronização) ou você cria uma.'
                    }
                />
            ) : null}
            {results.length > 0 ? (
                <>
                    <p className="text-xs text-zinc-500">
                        {total} regra(s){filtered ? ' com estes filtros' : ''}
                    </p>
                    <RulesTable
                        rules={results}
                        canEdit={canEdit}
                        busy={rules.busy}
                        onEdit={openForm}
                        onToggle={toggle}
                        onDelete={setDeleting}
                    />
                    <ReviewPager
                        offset={filters.offset}
                        shown={Math.min(RULES_PAGE_SIZE, results.length)}
                        total={total}
                        onChange={(offset) => setFilters((f) => ({ ...f, offset }))}
                    />
                </>
            ) : null}
            {form ? (
                <RuleFormDialog
                    rule={form === 'new' ? null : form}
                    accounts={accounts.data ?? []}
                    saving={rules.busy}
                    error={rules.actionError}
                    onSubmit={submit}
                    onCancel={close}
                />
            ) : null}
            {deleting ? (
                <ConfirmDialog
                    title="Excluir regra"
                    message={`Excluir a regra de ${describeRuleSupplier(deleting).title}? ${deleting.origin === 'history' ? 'Ela volta na próxima atualização do histórico; para impedir, desative em vez de excluir.' : 'Documentos novos deste fornecedor deixam de receber a conta sugerida.'}`}
                    confirmLabel="Excluir"
                    onConfirm={() => {
                        setNotice('')
                        rules.remove.mutate(deleting.id, {
                            onSuccess: () => {
                                setDeleting(null)
                                setNotice('Regra excluída.')
                            },
                            onError: () => setDeleting(null),
                        })
                    }}
                    onCancel={() => setDeleting(null)}
                />
            ) : null}
        </div>
    )
}
