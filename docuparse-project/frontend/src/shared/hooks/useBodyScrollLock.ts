import { useEffect } from 'react'

/**
 * Trava o scroll do `document.body` enquanto o componente estiver montado —
 * pra modais/drawers em `position: fixed`, evitando que o fundo role atrás do
 * overlay (e o par de scrollbars que isso gera). Restaura o valor anterior ao
 * desmontar; modais aninhados funcionam porque o de dentro sempre desmonta
 * antes do de fora.
 */
export function useBodyScrollLock(active = true): void {
    useEffect(() => {
        if (!active) return
        const previous = document.body.style.overflow
        document.body.style.overflow = 'hidden'
        return () => {
            document.body.style.overflow = previous
        }
    }, [active])
}
