---
title: Testes instáveis do backend-core - relógio do dev container e tracing
type: note
permalink: docuparser/reference/testes-instaveis-do-backend-core-relogio-do-dev-container-e-tracing
tags:
- testes
- flaky
- jwt
- tracing
- backend-core
---

# Testes instáveis do backend-core: relógio do dev container e tracing

Corrigido na branch `fix/flaky-core-tests` (commit b3eafbb6), em 2026-11-26.

## 401 aleatório em testes de API
- [causa] O relógio do dev container (WSL2) volta ~6s a cada poucos segundos quando a hora é ressincronizada. Medido: 25 saltos para trás em 2 minutos. #relogio
- [sintoma] Um JWT emitido no `setUp` fica com `iat` "no futuro"; o PyJWT 2.13 recusa (`ImmatureSignatureError`) e o simplejwt devolve o genérico "Token is invalid" → 401 em um teste qualquer, diferente a cada rodada. `KeyError: 'results'` / `'id'` em testes de API costuma ser o corpo desse 401. #jwt
- [correcao] `backend-core/conftest.py` define `rest_framework_simplejwt.state.token_backend.leeway = 30` depois do `django.setup()`. O `token_backend` é um singleton montado na importação, então `override_settings(SIMPLE_JWT=...)` não o alcança. #jwt
- [pendente] Produção não tem `LEEWAY` no `SIMPLE_JWT`; o servidor de dev pode sofrer o mesmo salto de relógio. Não alterado sem decisão do usuário.

## Testes de tracing dependiam de USE_TELEMETRY=true
- [causa] Com `USE_TELEMETRY=false` (padrão do `.env`), o provider global fica como `ProxyTracerProvider` (sem `add_span_processor`) e o `requests` não é instrumentado.
- [correcao] Fixture de sessão `sdk_tracer_provider` em `documents/tests/conftest.py`: monta o `TracerProvider` do SDK como o `configure_tracing()` faz (com o `RedactingSpanProcessor`, que é quem adiciona `net.peer.name`), instrumenta o `requests` e não usa exporter.

## Testes defasados depois do plano de contas compartilhado
- [causa] O commit a760ca6e passou `LedgerAccount`/`SupplierRule` para o `ChartOfAccounts`. Os testes ainda criam `LedgerAccount(condominium=...)` e usam as rotas antigas.
- [status] `documents/tests/test_classification_pipeline.py` foi corrigido. Cerca de 68 testes em `accounting/tests/` continuam quebrados pelo mesmo motivo (63 com TypeError, o resto com 404 nas rotas que agora ficam sob `/charts-of-accounts/<id>/...`).

## Relações
- relates_to [[Bugs pré-existentes na suíte de testes (encontrados na impl. 018)]]
- relates_to [[USE_TELEMETRY torna OpenTelemetry opcional]]
