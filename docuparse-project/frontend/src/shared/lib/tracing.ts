import { registerInstrumentations } from '@opentelemetry/instrumentation'
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch'
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request'
import { ZoneContextManager } from '@opentelemetry/context-zone'
import { W3CTraceContextPropagator } from '@opentelemetry/core'
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http'
import { resourceFromAttributes } from '@opentelemetry/resources'
import { BatchSpanProcessor, WebTracerProvider } from '@opentelemetry/sdk-trace-web'

const CORE_URL = import.meta.env.VITE_BACKEND_CORE_URL ?? ''
const COM_URL = import.meta.env.VITE_BACKEND_COM_URL ?? ''
const OTLP_ENDPOINT = import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT ?? 'http://localhost:4318/v1/traces'

// Hosts que devem receber o cabeçalho traceparent/tracestate em chamadas
// cross-origin (contracts/tracing-conventions.md item 7). Em dev, CORE_URL/
// COM_URL ficam vazios (o proxy do Vite torna as chamadas same-origin, onde o
// cabeçalho já é enviado por padrão) — a lista fica vazia e nada precisa ser
// declarado.
const propagateTraceHeaderCorsUrls = [CORE_URL, COM_URL]
    .filter((url): url is string => Boolean(url))
    .map((url) => new RegExp(`^${url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`))

let initialized = false

/** Bootstrap único do SDK Web (contracts/tracing-conventions.md item 1). Deve
 * ser chamado uma única vez, antes de qualquer chamada de API. */
export function initTracing(): void {
    if (initialized) return
    initialized = true

    const provider = new WebTracerProvider({
        resource: resourceFromAttributes({
            'service.name': import.meta.env.VITE_OTEL_SERVICE_NAME ?? 'frontend',
            'deployment.environment': import.meta.env.VITE_DEPLOYMENT_ENVIRONMENT ?? 'development',
        }),
        spanProcessors: [new BatchSpanProcessor(new OTLPTraceExporter({ url: OTLP_ENDPOINT }))],
    })

    provider.register({
        contextManager: new ZoneContextManager(),
        propagator: new W3CTraceContextPropagator(),
    })

    registerInstrumentations({
        tracerProvider: provider,
        instrumentations: [
            new FetchInstrumentation({ propagateTraceHeaderCorsUrls }),
            new XMLHttpRequestInstrumentation({ propagateTraceHeaderCorsUrls }),
        ],
    })
}
