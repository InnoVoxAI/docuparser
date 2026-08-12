import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../__tests__/mocks/server'
import { initTracing } from './tracing'

// T067 — confirma que, depois do bootstrap do SDK Web (contracts/tracing-conventions.md
// item 1), uma chamada fetch de saída inclui o cabeçalho traceparent (W3C Trace
// Context), propagado automaticamente pela FetchInstrumentation registrada em initTracing().
describe('tracing', () => {
    it('includes a valid traceparent header on an outgoing fetch call', async () => {
        let capturedTraceparent: string | null = null

        server.use(
            http.get('/api/tracing-test', ({ request }) => {
                capturedTraceparent = request.headers.get('traceparent')
                return HttpResponse.json({ ok: true })
            }),
        )

        initTracing()

        const response = await fetch('/api/tracing-test')
        await response.json()

        expect(capturedTraceparent).not.toBeNull()
        // Formato W3C Trace Context: version-traceId(32 hex)-spanId(16 hex)-flags(2 hex)
        expect(capturedTraceparent).toMatch(/^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$/)
    })

    it('is idempotent — calling initTracing() again does not throw or re-register instrumentation', () => {
        expect(() => {
            initTracing()
            initTracing()
        }).not.toThrow()
    })
})
