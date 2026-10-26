import { useMemo } from 'react'
import type { Account } from '../schemas/registry'
import { buildAccountTree, type AccountNode } from '../utils'

const NO_FLAGS: ReadonlySet<string> = new Set()

function Branch({ node, depth, flagged }: { node: AccountNode; depth: number; flagged: ReadonlySet<string> }) {
    const { account } = node
    return (
        <li>
            <div
                className={`flex gap-2 py-0.5 text-sm ${account.is_active ? 'text-zinc-800' : 'text-zinc-400 line-through'}`}
                style={{ paddingLeft: `${depth}rem` }}
            >
                <span className="shrink-0 tabular-nums text-zinc-500">{account.code}</span>
                <span className={node.children.length ? 'font-medium' : ''}>{account.name}</span>
                {flagged.has(account.id) ? (
                    <span className="rounded bg-amber-50 px-1.5 text-xs text-amber-700 ring-1 ring-amber-200">
                        sem conta pai
                    </span>
                ) : null}
            </div>
            {node.children.length > 0 ? (
                <ul>
                    {node.children.map((child) => (
                        <Branch key={child.account.id} node={child} depth={depth + 1} flagged={flagged} />
                    ))}
                </ul>
            ) : null}
        </li>
    )
}

/** Contas do plano em árvore (somente leitura), pela hierarquia do código pontuado. */
export function AccountTree({
    accounts,
    flagged = NO_FLAGS,
}: {
    accounts: Account[]
    /** Códigos a destacar como "sem conta pai". */
    flagged?: ReadonlySet<string>
}) {
    const roots = useMemo(() => buildAccountTree(accounts), [accounts])
    return (
        <ul aria-label="Contas do plano" className="max-h-96 overflow-y-auto">
            {roots.map((node) => (
                <Branch key={node.account.id} node={node} depth={0} flagged={flagged} />
            ))}
        </ul>
    )
}
