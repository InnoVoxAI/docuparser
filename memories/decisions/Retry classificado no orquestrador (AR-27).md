---
title: Retry classificado no orquestrador (AR-27)
type: note
permalink: docuparser/decisions/retry-classificado-no-orquestrador-ar-27
tags:
- orquestrador
- retry
- ocr
- langextract
- AR-27
---

# Retry classificado no orquestrador (AR-27)

Data: 2026-11-27. Branch `fix/ar-27-retry-classificado`, a partir de `dev`. O usuário escolheu as opções **A + 2 + padrão vazio**.

## Contexto
Antes, o `@task` (`shared/docuparse_orchestrator/decorators.py`) repetia a função inteira 3x com tenacity, para qualquer exceção. Cada tentativa do `ocr_task` chamava de novo o OCR pago (OpenRouter), mesmo num 400 ou numa falha de storage.

## Decisão
- **Retry opt-in:** `task(..., retry_on=(...))`, com padrão `()` (sem retry). Só `ocr_task` e `extraction_task` declaram `retry_on=(TransientServiceError,)`. `validation_decision_task` segue com `max_attempts=1`.
- **A classificação fica nos clientes do core** (opção A): `backend-core/documents/services/service_errors.py` tem `request_json`, `ServiceError`, `TransientServiceError` e `PermanentServiceError` (com `service` e `status_code`). `OCRClient` e `LangExtractClient` usam esse módulo. O `shared` não sabe nada de HTTP.
- **Transitório, critério conservador** (opção 2, porque as duas chamadas são pagas): `ConnectTimeout`, `ConnectionError`, HTTP 429, 502, 503 e 504.
- **Permanente:** os outros 4xx, **HTTP 500**, **`ReadTimeout`** e JSON inválido.

## Por quê
- [fato] O backend-ocr devolve HTTP 500 para qualquer erro do OpenRouter, inclusive 400/401/402 (`backend-ocr/infrastructure/engines/openrouter_engine.py` levanta RuntimeError e `api/routes/document.py` responde "Erro interno"). Por isso um 500, visto do core, pode ser permanente. #ocr
- [fato] Um `ReadTimeout` quer dizer que o pedido chegou: o OCR provavelmente rodou e foi cobrado. #custo
- [melhoria] Se o backend-ocr passar a repassar o status real do OpenRouter (429 vira 503, 4xx vira 4xx), o 500 pode virar transitório. Sem AR aberta. #ocr

## Efeitos
- [fato] `TaskExecution.attempt` vale 1 num erro permanente e N no esgotamento. A gravação continua só na tentativa final.
- [fato] `error_type` no TaskExecution e em `metadata.extraction`: `TransientServiceError` ou `PermanentServiceError`, e a mensagem traz o serviço e o status HTTP.
- [fato] Erro de storage ou de banco depois do OCR não repete mais a chamada paga.

## Testes
- Aceite em `backend-core/orchestrator/tests/test_document_pipeline_integration.py`: 400 gera 1 chamada; ConnectTimeout gera 3; 500 e ReadTimeout geram 1; 503 seguido de 200 dá attempt=2.
- Resultados: esse arquivo, 6 passed; shared/tests, 63 passed; documents + orchestrator, 269 passed.

## Relações
- part_of [[Revisão de arquitetura 2026-11]]
