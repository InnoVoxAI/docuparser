# Orquestrador leve de tasks (POC) — comparação com Camunda

## O que foi construído

Uma POC de orquestração de tasks fixas/codificadas, rodando **dentro do
processo Django** (`backend-core`), sem motor BPM nem worker separado:

1. **`shared/docuparse_orchestrator/`** — biblioteca Python pura:
   - `results.py` — `TaskResult`/`TaskError`, o "estado" padronizado que uma
     task retorna (`status`, `payload`, `error`, `task_id`, `run_id`,
     `attempt`, `duration_ms`).
   - `decorators.py` — `@task`: span OTel por execução, retry com backoff
     exponencial (`tenacity`), persiste um `TaskExecution` por tentativa
     final (nunca por tentativa intermediária), nunca levanta — devolve
     sempre um `TaskResult`.
   - `context.py` — `orchestration_run(nome)`: agrupa tasks de uma mesma
     cadeia sob um `run_id` comum (`uuid4`, não o `trace_id` do OTel — ver
     "Trade-offs" abaixo) e persiste um `OrchestrationRun`
     (RUNNING/COMPLETED/FAILED).
   - `persistence.py` — protocolo de escrita (injeta um writer fake nos
     testes unitários, sem precisar de Postgres) e o writer Django padrão,
     reaproveitando a denylist de redação já usada pelo tracing
     (`shared/docuparse_observability/redaction.py`) antes de gravar
     `payload` no banco.

2. **`backend-core/orchestrator/`** — app Django (tenant-scoped, como
   `documents`) com os dois modelos: `OrchestrationRun`, `TaskExecution`.

3. **O pipeline real instrumentado** (upload → OCR → extração → aprovação
   humana, rastreado a partir da chamada que o frontend faz no upload —
   nenhuma referência ao BPMN antigo foi usada como base):
   - **Run A — `document_processing`**
     (`documents/services/processing_queue.py`): substitui o
     `try/except` manual que existia (`_run_processing_safely`) por
     `orchestration_run` encadeando `ocr_task` → `extraction_task`
     (`documents/services/ocr_processor.py`).
   - **Run B — `document_validation`** (`documents/views.py`,
     `document_validation_view`): a gravação da decisão de aprovação/rejeição
     vira `validation_decision_task`, com `max_attempts=1` (não é seguro
     repetir um `.create()` de auditoria).

## Trade-offs observados na prática

- **`run_id` não pôde ser o `trace_id` do OTel.** A ideia inicial era usar o
  `trace_id` do span raiz como identificador de execução. Ao integrar no
  pipeline real, descobrimos que o cruzamento request→thread já existente
  (`capture_current_span_link`) usa `Link`, não parent-child — a thread em
  background já abre um trace novo. Resolvido gerando um `uuid4()` próprio
  em `orchestration_run`, independente do tracing.
- **Duas execuções, não uma.** OCR/extração rodam numa thread de background
  disparada pelo upload; a aprovação humana é uma request separada,
  possivelmente dias depois. Não há uma única `OrchestrationRun` cobrindo
  "upload até aprovação" — só duas, relacionáveis por `document_id`, não por
  `run_id` compartilhado. Uma versão futura que quisesse isso precisaria de
  um `orchestration_run` capaz de "pausar" entre requests, o que sai do
  escopo de fluxo fixo simples desta POC.
- **Nem toda task pode ter retry.** `validation_decision_task` roda com
  `max_attempts=1` porque grava `ValidationDecision`/`ExtractionFieldVersion`
  via `.create()` — repetir a tentativa duplicaria registros de auditoria em
  vez de só reagir a uma falha transitória de rede. Retry automático só é
  seguro em tasks idempotentes (OCR e extração usam `save`/`update_or_create`,
  por isso toleram retry).
- **O que se perde vs. Camunda**: modelagem visual BPMN, suporte nativo a
  sub-processos, roteamento dinâmico de fluxo, e um motor com histórico de
  execução já pronto (Operate/Tasklist) — aqui esse histórico teve que ser
  desenhado e implementado à mão (`OrchestrationRun`/`TaskExecution`).
- **O que se ganha**: nenhum motor externo, nenhum worker/serviço separado
  para operar (o `camunda-workers` inteiro deixa de ser necessário para este
  fluxo), execução e retry testáveis sem infraestrutura (os testes de
  `@task`/`orchestration_run` rodam sem banco de dados), e o que antes era um
  `try/except` manual e silencioso vira histórico consultável.

## Conclusão / recomendação

A POC atende o caso de uso atual: um fluxo fixo, conhecido em tempo de
código (upload → OCR → extração → aprovação), sem necessidade de
sub-processos ou modelagem visual. Para esse tipo de fluxo, o overhead
operacional do Camunda (Zeebe, Operate, Tasklist, Elasticsearch) deixa de se
justificar frente a uma biblioteca Python simples rodando no mesmo processo.

Recomendação: **adotar esta abordagem para os fluxos fixos existentes** e
tratar o Camunda como não necessário para o escopo atual do produto. Reavaliar
Camunda (ou alternativa) apenas se surgir um requisito real de modelagem
dinâmica/visual de fluxo, ou de orquestração cross-service que precise
sobreviver a reinícios de processo — nenhum dos dois casos existe hoje.
