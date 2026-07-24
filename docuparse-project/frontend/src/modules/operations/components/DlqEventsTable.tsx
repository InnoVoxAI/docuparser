import { AlertTriangle } from 'lucide-react'
import { EmptyState } from '../../../shared/components'
import { formatDate } from '../../../shared/utils'
import type { DlqEvent } from '../types'

export function DlqEventsTable({
    stream,
    events,
    selectedEvent,
    onSelectEvent,
}: {
    stream: string
    events: DlqEvent[]
    selectedEvent: DlqEvent | null
    onSelectEvent: (event: DlqEvent) => void
}) {
    return (
        <div className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-4 py-3">
                <div className="text-sm font-semibold">{stream}</div>
                <div className="mt-1 text-xs text-zinc-500">Selecione um evento para ver erro e payload original.</div>
            </div>
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-zinc-200 text-sm">
                    <thead className="bg-zinc-50 text-left text-xs uppercase text-zinc-500">
                        <tr>
                            <th className="px-4 py-3">Data</th>
                            <th className="px-4 py-3">Origem</th>
                            <th className="px-4 py-3">Evento</th>
                            <th className="px-4 py-3">Erro</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                        {events.map((event) => (
                            <tr
                                key={event.id}
                                onClick={() => onSelectEvent(event)}
                                className={`cursor-pointer hover:bg-zinc-50 ${selectedEvent?.id === event.id ? 'bg-zinc-50' : ''}`}
                            >
                                <td className="whitespace-nowrap px-4 py-3 text-zinc-600">
                                    {formatDate(event.occurred_at)}
                                </td>
                                <td className="whitespace-nowrap px-4 py-3">{event.source || '-'}</td>
                                <td className="px-4 py-3">
                                    <div className="font-medium">{event.event_type || '-'}</div>
                                    <div className="max-w-[220px] truncate text-xs text-zinc-500">
                                        {event.event_id || '-'}
                                    </div>
                                </td>
                                <td className="px-4 py-3">
                                    <div className="font-medium text-red-700">{event.error_type || '-'}</div>
                                    <div className="max-w-[360px] truncate text-xs text-zinc-500">
                                        {event.error || '-'}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {events.length === 0 ? <EmptyState icon={AlertTriangle} text="Nenhum evento nesta DLQ." /> : null}
        </div>
    )
}
