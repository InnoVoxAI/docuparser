---
title: '020 - OpenTelemetry Tracing: Fase 7 (Polish)'
type: note
permalink: docuparser/features/020-opentelemetry-tracing-fase-7-polish
tags:
- feature-020
- opentelemetry
- observability
---

## Status

Fase 7 (Polish & Cross-Cutting Concerns) da feature `020-opentelemetry-tracing` implementada e validada (T062-T068) — **todas as 4 histórias de usuário e todas as 7 fases da feature estão completas**. Validação rodada contra o stack Docker real e completo (não simulada), incluindo um upload real com OCR/extração reais via OpenRouter.

## O que mudou

- **Tail sampling** (`otel-collector-config.yaml`, T062): processor `tail_sampling` com duas políticas OR — `errors-policy` (`status_code=ERROR`, retenção incondicional) e `probabilistic-policy` (`sampling_percentage: ${env:OTEL_TAIL_SAMPLING_PERCENTAGE}`, nova env var no `docker-compose.yml`, default `100`). Validado com `telemetrygen` real: a 0% probabilístico, só os traces `ERROR` sobrevivem no Jaeger.
- **Limite de RAM** (T063): sem ajuste — `otel-collector`/`jaeger` medidos em 40-190MiB / 60-63MiB (via `docker stats` + carga sintética), uma ordem de magnitude abaixo do teto de 2GB da Constitution. Nenhum outro serviço do compose define `mem_limit` explícito, então não foi adicionado só para estes dois.
- **Teste de resiliência** (T064, `test_tracing_resilience.py` novo): segundo `BatchSpanProcessor` apontando pra porta ligada-e-fechada (conexão recusada determinística); chamada real via `OCRClient` completa em <1s (timeout de export é 2s) — prova que a exportação assíncrona nunca bloqueia. Também validado ao vivo: `docker compose stop otel-collector` + requisições reais, todas 200/<15ms.
- **Benchmark de overhead** (T065, `research.md` R13): `git worktree` no commit pré-instrumentação (`7a9ce49`) vs HEAD, ambos nativos no host (não Docker, pra não confundir overhead de instrumentação com overhead de rede de container). `backend-core /api/ocr/health`: overhead ≤0.42% do orçamento de 200ms. `backend-ocr /health` (proxy do endpoint de processamento — rodar OCR real 500x é dominado por latência de engine/API externa, não por tracing): overhead ≤0.0047% do orçamento de 30s.
- **`docs/TECHNICAL.md`** (T066): nova seção "Observabilidade e Rastreamento Distribuído".
- **`tracing.test.ts`** (T067, frontend): MSW captura o header `traceparent` de uma chamada `fetch()` real após `initTracing()`, valida formato W3C. 18 falhas pré-existentes na suíte do frontend (bug `undici`/`AbortSignal` do MSW com React Router) não relacionadas — confirmado rodando a suíte com/sem o arquivo novo.

## Bug encontrado e corrigido (T068, não estava nos tasks originais, mas quebra US1 no caminho padrão)

`backend-core/documents/services/processing_queue.py::submit_document_processing` — o caminho de "auto-process" via `ThreadPoolExecutor`, **usado por padrão** (`DOCUPARSE_AUTO_PROCESS_OCR=true`) sempre que um documento é recebido — despachava o processamento OCR pra uma thread do pool sem propagar o contexto OTel ativo. `ThreadPoolExecutor.submit()` não herda `contextvars` automaticamente, então a chamada HTTP real a `backend-ocr` (e em cascata a `langextract-service`) produzia um **trace completamente desconectado** (`refs=[]`, nem span nem Link) — quebrando silenciosamente a promessa central de US1 pro fluxo padrão que o próprio `quickstart.md` demonstra. Só foi descoberto inspecionando o Jaeger de ponta a ponta com um upload real; os testes unitários com `InMemorySpanExporter` não exercitam o `ThreadPoolExecutor` de verdade.

**Fix**: novo helper `capture_current_span_link()` em `shared/docuparse_observability/tracing.py` (captura o `SpanContext` ativo antes do `.submit()`), usado em `processing_queue.py` (`submit_document_processing`/`submit_document_langextract`) e em `ocr_processor.py` (`start_document_ocr_thread` — mesmo padrão, mas hoje sem chamador ativo no repo, código morto). Cada worker agora abre seu próprio span (`document.ocr_processing`/`document.langextract_processing`) com `links=[link]` — mesmo padrão de Span Link de R3/R4 (fronteiras de evento/Zeebe), aplicado aqui a uma fronteira interna de thread pool — e grava a exceção explicitamente (`span.record_exception`/`set_status(ERROR)`) já que o `try/except` do worker a captura sem re-lançar.

**Cuidado operacional descoberto nesta sessão**: rodar `uv sync`/`uv run` diretamente no diretório real do serviço (não num worktree separado) regenera o `.venv` local com binários macOS — como `docker-compose.yml` faz bind-mount de `./backend-core:/app` (sem volume separado pro `.venv`), isso quebra o container em execução (`FileNotFoundError: /app/.venv/bin/python3`, o interpretador do venv host não existe dentro do container Linux). Aconteceu 2x nesta sessão (durante o benchmark T065). Fix: `rm -rf backend-core/.venv` + `docker compose restart backend-core` (o `CMD` do container faz `uv run`, que resincroniza o venv certo). **Sempre usar `git worktree` separado pra rodar `uv sync`/testes locais em serviços que têm container ativo.**

## Verificação end-to-end (upload real, stack Docker completo)

Upload via `POST /api/v1/documents/manual` (`backend-com`) → confirmado no Jaeger, cadeia de 3 traces conectados por Link:
1. `backend-com`: `POST /api/v1/documents/manual` (trace de origem)
2. `backend-core`: `POST api/ocr/events/document-received` + `document.received process` — `FOLLOWS_FROM` → trace 1
3. `backend-core`: `document.ocr_processing` (span novo, pós-fix) — `FOLLOWS_FROM` → trace 2 — contendo como filhos diretos (`CHILD_OF`, mesmo trace) `POST /api/v1/process` real (`backend-ocr`, 34.9s) e `POST /api/v1/extract` real (`langextract-service`, 29s)

Passo 4 (resiliência) e passo 5 (ausência de dado sensível — atributos do trace real inspecionados, só chaves da allowlist) confirmados ao vivo. Passo 6: `documents/tests/` completo rodado **dentro do container** (`docker compose exec backend-core`, evita colidir com o `.venv` do host) — 102/102 passed, incluindo os 5 testes de tracing.

## Próximos passos

Feature `020-opentelemetry-tracing` completa (todas as 7 fases, T001-T068). Nenhum próximo passo pendente desta feature. Ver [[../../docs/specs/020-opentelemetry-tracing/tasks.md|tasks.md]]. Ver também [[020 - OpenTelemetry Tracing- Fase 3 (US1 - MVP)]].
