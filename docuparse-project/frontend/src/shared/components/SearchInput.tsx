export function SearchInput({
    value,
    onChange,
    placeholder = 'Buscar...',
}: {
    value: string
    onChange: (value: string) => void
    placeholder?: string
}) {
    return (
        <input
            type="search"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="h-8 w-56 rounded-md border border-zinc-300 bg-white px-3 text-sm placeholder-zinc-400 outline-none focus:border-zinc-500"
        />
    )
}
