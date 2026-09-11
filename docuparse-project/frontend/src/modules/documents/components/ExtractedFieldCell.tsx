import { X } from 'lucide-react'
import { humanizeFieldName } from '../utils'
import type { FieldRow } from '../types'

/** Campos curtos (datas, códigos, números de documento) ocupam 1 das 3
 * colunas em telas largas — vários cabem lado a lado. Campos médios (nomes,
 * e-mails) ocupam 2. Valores longos (endereços, chaves de acesso) tomam a
 * linha inteira. */
function spanClassFor(value: string): string {
    const length = value.trim().length
    if (length > 40) return 'col-span-full'
    if (length > 14) return 'lg:col-span-2'
    return ''
}

/** Um campo extraído na grade da tela de Validação: rótulo legível (não a
 * chave técnica) acima de um valor editável, com um "x" pra remover o campo. */
export function ExtractedFieldCell({
    row,
    onChangeValue,
    onRemove,
}: {
    row: FieldRow
    onChangeValue: (value: string) => void
    onRemove: () => void
}) {
    const label = humanizeFieldName(row.name)
    return (
        <div className={spanClassFor(row.value)}>
            {/* min-h reserva espaço pra 2 linhas — sem isso, um rótulo longo numa
            célula da mesma linha empurra só o próprio input pra baixo,
            desalinhando com os campos vizinhos de rótulo curto. */}
            <span className="mb-1 block min-h-8 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                {label}
            </span>
            <div className="relative">
                <input
                    value={row.value}
                    onChange={(event) => onChangeValue(event.target.value)}
                    className="input pr-8"
                    aria-label={label}
                />
                <button
                    type="button"
                    onClick={onRemove}
                    aria-label={`Remover campo ${label}`}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700"
                >
                    <X size={14} aria-hidden="true" />
                </button>
            </div>
        </div>
    )
}
