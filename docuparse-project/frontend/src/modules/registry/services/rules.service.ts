import { api } from '../../../shared/lib/http'
import {
    RULES_PAGE_SIZE,
    ruleSchema,
    rulesPageSchema,
    type NewRuleInput,
    type Rule,
    type RuleFilters,
    type RulePatch,
    type RulesPage,
} from '../schemas/rules'

const base = (chartId: string) => `/charts-of-accounts/${chartId}/supplier-rules`

export async function fetchRules(chartId: string, filters: RuleFilters): Promise<RulesPage> {
    const response = await api.get<unknown>(base(chartId), {
        params: {
            search: filters.search || undefined,
            origin: filters.origin || undefined,
            prefills: filters.prefills || undefined,
            limit: RULES_PAGE_SIZE,
            offset: filters.offset,
        },
    })
    return rulesPageSchema.parse(response.data)
}

export async function createRule(chartId: string, input: NewRuleInput): Promise<Rule> {
    const response = await api.post<unknown>(base(chartId), input)
    return ruleSchema.parse(response.data)
}

/** Editar torna a regra manual no backend: a atualização do histórico não a desfaz. */
export async function updateRule(chartId: string, ruleId: string, patch: RulePatch): Promise<Rule> {
    const response = await api.patch<unknown>(`${base(chartId)}/${ruleId}`, patch)
    return ruleSchema.parse(response.data)
}

export async function deleteRule(chartId: string, ruleId: string): Promise<void> {
    await api.delete(`${base(chartId)}/${ruleId}`)
}
