# Contrato: Campo `trace_context` no schema base de evento

Referência: `docuparse-project/contracts/events/schemas.py`. Ver [[../data-model.md]] e [[../research.md]] R4.

## Antes

```python
class BaseEvent(BaseModel):
    correlation_id: UUID = Field(default_factory=uuid4)
    # ... demais campos existentes (event_type, tenant_id, timestamp, etc.)
```

## Depois

```python
class BaseEvent(BaseModel):
    correlation_id: UUID = Field(default_factory=uuid4)
    trace_context: dict[str, str] | None = None
    # ... demais campos existentes, inalterados
```

## Regras do contrato

1. **Retrocompatível por padrão `None`** — nenhum publisher existente é obrigado a preencher o campo para o evento continuar sendo um `BaseEvent` válido.
2. **Publishers instrumentados DEVEM preencher** `trace_context` com o resultado de `opentelemetry.propagate.inject()` (um dict simples de string→string, tipicamente `{"traceparent": "00-...-...-01"}`) no momento da publicação, dentro de `shared/docuparse_events`.
3. **Consumers DEVEM tratar `None` como "sem contexto de origem"** — iniciam um novo trace raiz em vez de falhar (nenhuma validação deve rejeitar um evento por falta desse campo).
4. **Nunca usado para lógica de negócio** — `trace_context` é exclusivamente para observabilidade; nenhuma regra de roteamento, autorização ou processamento de evento deve inspecionar ou depender do seu conteúdo. `correlation_id` continua sendo o identificador de negócio.
5. **Serviços afetados por este contrato**: qualquer publisher/consumidor de evento via `shared.docuparse_events` — hoje isso inclui `backend-com` (indiretamente, ao dar origem ao fluxo), `backend-core` (`event_consumers.py`), `backend-ocr` (`ocr_event_worker.py`), `layout-service` (`layout_event_worker.py`), `langextract-service` (`extraction_event_worker.py`).
