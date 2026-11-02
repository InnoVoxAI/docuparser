import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { NewRuleInput, RuleFilters, RulePatch } from '../schemas/rules'
import { createRule, deleteRule, fetchRules, updateRule } from '../services/rules.service'
import { readFieldError } from '../utils'
import { registryKeys } from './queryKeys'

/** Regras de fornecedor de um plano, filtradas e paginadas, e as ações de editar. */
export function useRules(chartId: string | null, filters: RuleFilters) {
    const queryClient = useQueryClient()
    const query = useQuery({
        queryKey: registryKeys.rules(chartId ?? '', filters),
        queryFn: () => fetchRules(chartId ?? '', filters),
        enabled: Boolean(chartId),
        placeholderData: keepPreviousData,
        staleTime: 10_000,
    })
    const refresh = () => queryClient.invalidateQueries({ queryKey: [...registryKeys.all, 'rules'] })
    const id = chartId ?? ''

    const create = useMutation({ mutationFn: (input: NewRuleInput) => createRule(id, input), onSuccess: refresh })
    const update = useMutation({
        mutationFn: (input: { ruleId: string; patch: RulePatch }) => updateRule(id, input.ruleId, input.patch),
        onSuccess: refresh,
    })
    const remove = useMutation({ mutationFn: (ruleId: string) => deleteRule(id, ruleId), onSuccess: refresh })

    const failure = create.error ?? update.error ?? remove.error
    return {
        page: query.data,
        loading: query.isLoading,
        loadError: query.error ? readFieldError(query.error, 'Nao foi possivel carregar as regras.') : '',
        create,
        update,
        remove,
        busy: create.isPending || update.isPending || remove.isPending,
        actionError: failure ? readFieldError(failure, 'Nao foi possivel salvar a regra.') : '',
        resetErrors: () => {
            create.reset()
            update.reset()
            remove.reset()
        },
    }
}
