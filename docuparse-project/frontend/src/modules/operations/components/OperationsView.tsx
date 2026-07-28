import { useState } from 'react'
import { Alert } from '../../../shared/components'
import { readError } from '../../../shared/utils'
import { useDlqSummaryQuery } from '../hooks/useDlqSummaryQuery'
import { useDlqEventsQuery } from '../hooks/useDlqEventsQuery'
import { useRequeueMutation } from '../hooks/useRequeueMutation'
import type { DlqEvent } from '../types'
import { DlqStreamSummary } from './DlqStreamSummary'
import { DlqEventsTable } from './DlqEventsTable'
import { DlqEventDetail } from './DlqEventDetail'

const DEFAULT_DLQ_STREAM = 'ocr.completed.dlq'

export function OperationsView() {
    const [selectedStream, setSelectedStream] = useState(DEFAULT_DLQ_STREAM)
    const [selectedEvent, setSelectedEvent] = useState<DlqEvent | null>(null)
    // Mensagem de resultado de uma ação de reenfileiramento (simular/executar);
    // erros de carregamento das queries usam o próprio estado de erro delas
    // (ver `loadError` abaixo), mas caem no mesmo Alert quando não há `message`.
    const [message, setMessage] = useState('')
    const [messageTone, setMessageTone] = useState<'neutral' | 'error'>('neutral')

    const summaryQuery = useDlqSummaryQuery()
    const eventsQuery = useDlqEventsQuery(selectedStream)
    const { requeueEvent, requeueing } = useRequeueMutation()

    const loading = summaryQuery.isFetching || eventsQuery.isFetching
    const loadError = summaryQuery.error ?? eventsQuery.error
    const bannerMessage = message || (loadError ? readError(loadError, 'Nao foi possivel carregar as DLQs.') : '')
    const bannerTone = message ? messageTone : 'error'

    const refresh = () => {
        setMessage('')
        setMessageTone('neutral')
        summaryQuery.refetch()
        eventsQuery.refetch()
    }

    const selectStream = (stream: string) => {
        setSelectedStream(stream)
        setSelectedEvent(null)
        setMessage('')
        setMessageTone('neutral')
    }

    const requeueSelectedEvent = async ({ execute }: { execute: boolean }) => {
        if (!selectedEvent || requeueing) {
            return
        }
        if (
            execute &&
            !window.confirm(
                'Reenfileirar este payload original para reprocessamento? O registro da DLQ sera mantido para auditoria.',
            )
        ) {
            return
        }
        setMessage('')
        setMessageTone('neutral')
        try {
            const result = await requeueEvent({ stream: selectedStream, id: selectedEvent.id, execute })
            const target = result.target_stream || selectedEvent.original_stream || selectedStream
            if (execute) {
                setMessage(`Evento reenfileirado em ${target}. O item original permanece na DLQ para auditoria.`)
            } else {
                setMessage(`Simulacao OK: este evento sera enviado para ${target}.`)
            }
            setMessageTone('neutral')
        } catch (requestError) {
            setMessageTone('error')
            setMessage(readError(requestError, 'Nao foi possivel reenfileirar o evento.'))
        }
    }

    return (
        <div className="space-y-4">
            {bannerMessage ? <Alert tone={bannerTone}>{bannerMessage}</Alert> : null}
            {loading ? <Alert>Carregando operacoes...</Alert> : null}
            <DlqStreamSummary
                summary={summaryQuery.data}
                selectedStream={selectedStream}
                onSelectStream={selectStream}
                onRefresh={refresh}
            />
            <section className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
                <DlqEventsTable
                    stream={selectedStream}
                    events={eventsQuery.data}
                    selectedEvent={selectedEvent}
                    onSelectEvent={setSelectedEvent}
                />
                <DlqEventDetail
                    stream={selectedStream}
                    event={selectedEvent}
                    requeueing={requeueing}
                    onSimulate={() => requeueSelectedEvent({ execute: false })}
                    onRequeue={() => requeueSelectedEvent({ execute: true })}
                />
            </section>
        </div>
    )
}
