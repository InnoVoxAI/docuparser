export function KeyValueGrid({ values }: { values: Record<string, unknown> }) {
    return (
        <dl className="grid gap-2 sm:grid-cols-3">
            {Object.entries(values).map(([key, value]) => (
                <div key={key} className="rounded-md bg-zinc-50 px-3 py-2">
                    <dt className="text-xs uppercase text-zinc-500">{key}</dt>
                    <dd className="mt-1 text-sm font-medium">{String(value)}</dd>
                </div>
            ))}
        </dl>
    )
}
