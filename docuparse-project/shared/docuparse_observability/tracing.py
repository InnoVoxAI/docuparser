from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanProcessor
from opentelemetry.trace import Link

from docuparse_observability.redaction import is_denied

_DEFAULT_OTLP_ENDPOINT = "http://otel-collector:4317"
_EXPORT_TIMEOUT_SECONDS = 2

# `opentelemetry-instrumentation-{requests,httpx}` só emitem o atributo
# `net.peer.name` (contracts/tracing-conventions.md item 4, data-model.md) em
# métricas, nunca no span — o span client só recebe `network.peer.address`
# (novo semconv, exige OTEL_SEMCONV_STABILITY_OPT_IN=http/dup, ver abaixo).
# Normalizamos aqui para que o nome de atributo exigido pelo contrato chegue
# ao Collector, cujo allowlist (otel-collector-config.yaml) já espera
# `net.peer.name`, não `network.peer.address`.
_NET_PEER_NAME_KEY = "net.peer.name"
_NETWORK_PEER_ADDRESS_KEY = "network.peer.address"

_configured_services: set[str] = set()

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def is_telemetry_enabled() -> bool:
    """Liga/desliga OpenTelemetry via `USE_TELEMETRY` (default: desligado).

    Permite rodar sem um Collector disponível (ex.: servidores onde o
    Collector ainda não foi instalado) sem alterar código de cada serviço —
    `configure_tracing()` e as instrumentações de biblioteca (`XInstrumentor`)
    checam esta flag antes de fazer qualquer setup.
    """
    return os.environ.get("USE_TELEMETRY", "false").strip().lower() in _TRUTHY_VALUES


class RedactingSpanProcessor(SpanProcessor):
    """Remove atributos de span sensíveis antes da exportação (FR-006)."""

    def on_start(self, span, parent_context=None) -> None:  # noqa: ANN001
        return None

    def on_end(self, span: ReadableSpan) -> None:
        attributes = span.attributes
        if not attributes:
            return
        normalized = dict(attributes)
        changed = False
        if (
            _NET_PEER_NAME_KEY not in normalized
            and _NETWORK_PEER_ADDRESS_KEY in normalized
        ):
            normalized[_NET_PEER_NAME_KEY] = normalized[_NETWORK_PEER_ADDRESS_KEY]
            changed = True
        if any(is_denied(key) for key in normalized):
            normalized = {
                key: value for key, value in normalized.items() if not is_denied(key)
            }
            changed = True
        if not changed:
            return
        # ReadableSpan.attributes é um BoundedAttributes somente-leitura; a
        # única forma suportada de redigir/normalizar é substituir o dict inteiro.
        span._attributes = normalized

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def configure_tracing(service_name: str) -> None:
    """Bootstrap único do TracerProvider para o processo atual.

    Idempotente por `service_name` para que reimportações (testes, reload)
    não registrem exporters/processors duplicados. Nenhum serviço deve
    instanciar seu próprio TracerProvider/exporter diretamente (contrato 1).
    """
    if service_name in _configured_services:
        return

    if not is_telemetry_enabled():
        return

    # As instrumentações `requests`/`httpx` só marcam `error.type` no span de
    # saída (US3, data-model.md) quando o novo semconv HTTP está ativo; em
    # `http/dup` elas continuam emitindo os atributos antigos também, então
    # nada muda para o resto da allowlist. Precisa ser setado antes de
    # qualquer `XInstrumentor().instrument()` — o valor é lido e cacheado por
    # processo na primeira instrumentação (opentelemetry.instrumentation._semconv),
    # e todo bootstrap chama configure_tracing() antes de instrumentar.
    os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http/dup")

    resource = Resource.create(
        {
            "service.name": os.environ.get("OTEL_SERVICE_NAME", service_name),
            "service.version": os.environ.get("OTEL_SERVICE_VERSION", "0.0.0"),
            "deployment.environment": os.environ.get(
                "DEPLOYMENT_ENVIRONMENT", "development"
            ),
        }
    )
    provider = TracerProvider(resource=resource)

    # Ordem importa: a redação precisa rodar antes do processor que exporta.
    provider.add_span_processor(RedactingSpanProcessor())

    exporter = OTLPSpanExporter(
        endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", _DEFAULT_OTLP_ENDPOINT),
        timeout=_EXPORT_TIMEOUT_SECONDS,
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            exporter, export_timeout_millis=_EXPORT_TIMEOUT_SECONDS * 1000
        )
    )

    trace.set_tracer_provider(provider)
    _configured_services.add(service_name)


def capture_current_span_link() -> Link | None:
    """Captura o contexto do span ativo para propagar através de um limite
    que não herda `contextvars` automaticamente — `ThreadPoolExecutor.submit()`
    e `threading.Thread` rodam a função-alvo numa thread com contexto vazio,
    então sem isso trabalho despachado para outra thread perde a associação
    com o trace de origem (FR-007). Mesmo padrão de Link usado nas fronteiras
    de evento/Zeebe (research.md R3/R4), aplicado aqui a um limite interno de
    processo (thread pool), não uma fronteira entre serviços."""
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return Link(span_context)
