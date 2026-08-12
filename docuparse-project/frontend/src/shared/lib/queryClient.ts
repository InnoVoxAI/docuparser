import { QueryClient } from '@tanstack/react-query'

// `retry: false` preserva o comportamento pré-existente (fetch único, erro
// exibido imediatamente) das telas migradas — o monólito original nunca
// re-tentava uma requisição falha automaticamente.
export const queryClient = new QueryClient({
    defaultOptions: {
        queries: { retry: false },
    },
})
