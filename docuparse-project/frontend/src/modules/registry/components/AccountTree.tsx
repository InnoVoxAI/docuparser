import { useMemo } from 'react'
import type { Account } from '../schemas/registry'
import { buildAccountTree, type AccountNode } from '../utils'

function Branch({ node, depth }: { node: AccountNode; depth: number }) {
    const { account } = node
    return (
        <li>
            <div
                className={`flex gap-2 py-0.5 text-sm ${account.is_active ? 'text-zinc-800' : 'text-zinc-400 line-through'}`}
                style={{ paddingLeft: `${depth}rem` }}
            >
                <span className="shrink-0 tabular-nums text-zinc-500">{account.code}</span>
                <span className={node.children.length ? 'font-medium' : ''}>{account.name}</span>
            </div>
            {node.children.length > 0 ? (
                <ul>
                    {node.children.map((child) => (
                        <Branch key={child.account.id} node={child} depth={depth + 1} />
                    ))}
                </ul>
            ) : null}
        </li>
    )
}

/** Contas do plano em árvore (somente leitura), pela hierarquia do código pontuado. */
export function AccountTree({ accounts }: { accounts: Account[] }) {
    const roots = useMemo(() => buildAccountTree(accounts), [accounts])
    return (
        <ul aria-label="Contas do plano" className="max-h-96 overflow-y-auto">
            {roots.map((node) => (
                <Branch key={node.account.id} node={node} depth={0} />
            ))}
        </ul>
    )
}
