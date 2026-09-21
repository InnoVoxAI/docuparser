import { useState } from 'react'

/** Formulário inline pra adicionar um campo que o modelo não extraiu — o
 * único lugar da tela de Validação onde o nome do campo ainda é digitado
 * (campos já extraídos mostram só o rótulo, não editável). */
export function AddExtractedFieldForm({
    onAdd,
    onCancel,
}: {
    onAdd: (name: string, value: string) => void
    onCancel: () => void
}) {
    const [name, setName] = useState('')
    const [value, setValue] = useState('')
    return (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_1fr_auto_auto]">
            <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="input"
                placeholder="Nome do campo"
            />
            <input
                value={value}
                onChange={(event) => setValue(event.target.value)}
                className="input"
                placeholder="Valor"
            />
            <button
                type="button"
                disabled={!name.trim()}
                onClick={() => onAdd(name.trim(), value)}
                className="rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
                Adicionar
            </button>
            <button
                type="button"
                onClick={onCancel}
                className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100"
            >
                Cancelar
            </button>
        </div>
    )
}
