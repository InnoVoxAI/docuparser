from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanProcessor

_DEFAULT_OTLP_ENDPOINT = "http://otel-collector:4317"
_EXPORT_TIMEOUT_SECONDS = 2

# Denylist explícita (data-model.md): removida mesmo se alguma biblioteca de
# instrumentação tentar capturá-la. A allowlist correspondente não é aplicada
# aqui — instrumentações automáticas já não emitem atributos fora dela por
# padrão; este processor é a rede de segurança contra o que sobrar/escapar.
_DENYLIST_ATTRIBUTES = {"http.request.body", "http.response.body", "authorization"}
_DENYLIST_SUFFIXES = ("_token", "_secret", "_password")

_configured_services: set[str] = set()


class RedactingSpanProcessor(SpanProcessor):
    """Remove atributos de span sensíveis antes da exportação (FR-006)."""

    def on_start(self, span, parent_context=None) -> None:  # noqa: ANN001
        return None

    def on_end(self, span: ReadableSpan) -> None:
        attributes = span.attributes
        if not attributes or not any(_is_denied(key) for key in attributes):
            return
        # ReadableSpan.attributes é um BoundedAttributes somente-leitura; a
        # única forma suportada de redigir é substituir o dict inteiro.
        span._attributes = {
            key: value for key, value in attributes.items() if not _is_denied(key)
        }

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def _is_denied(key: str) -> bool:
    lowered = key.lower()
    return lowered in _DENYLIST_ATTRIBUTES or lowered.endswith(_DENYLIST_SUFFIXES)


def configure_tracing(service_name: str) -> None:
    """Bootstrap único do TracerProvider para o processo atual.

    Idempotente por `service_name` para que reimportações (testes, reload)
    não registrem exporters/processors duplicados. Nenhum serviço deve
    instanciar seu próprio TracerProvider/exporter diretamente (contrato 1).
    """
    if service_name in _configured_services:
        return

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
