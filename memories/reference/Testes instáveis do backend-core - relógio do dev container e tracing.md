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
- [correcao] `SIMPLE_JWT["LEEWAY"] = timedelta(seconds=30)` em `core/settings.py`, aplicado também em produção por decisão do usuário (commit d5d9abf4). Cobre o relógio do servidor oscilando e a diferença de relógio entre servidores. Coberto por `users/tests/test_jwt_clock_skew.py`, que falha sem a configuração. #jwt
- [decisao] Sobrescrever a tolerância só nos testes não funciona via `override_settings(SIMPLE_JWT=...)`: o `token_backend` do simplejwt é um singleton montado na importação.

## Testes de tracing dependiam de USE_TELEMETRY=true
- [causa] Com `USE_TELEMETRY=false` (padrão do `.env`), o provider global fica como `ProxyTracerProvider` (sem `add_span_processor`) e o `requests` não é instrumentado.
- [correcao] Fixture de sessão `sdk_tracer_provider` em `documents/tests/conftest.py`: monta o `TracerProvider` do SDK como o `configure_tracing()` faz (com o `RedactingSpanProcessor`, que é quem adiciona `net.peer.name`), instrumenta o `requests` e não usa exporter.

## Testes defasados depois do plano de contas compartilhado
- [causa] O commit a760ca6e passou `LedgerAccount`/`SupplierRule` para o `ChartOfAccounts`. Os testes ainda criam `LedgerAccount(condominium=...)` e usam as rotas antigas.
- [status] Corrigido: `documents/tests/test_classification_pipeline.py` (b3eafbb6) e os 68 testes de `accounting/tests/` (1b1700f0), agora com contas sob o plano e rotas `/charts-of-accounts/<id>/...`. A suíte completa do backend-core ficou verde: 579 passaram, 1 pulado.
- [regra] Um condomínio sem plano de contas não pode ter regras de fornecedor (400). A regra do condomínio vence a regra do plano. A regra de um condomínio não vale para os vizinhos do mesmo plano.

## Relações
- relates_to [[Bugs pré-existentes na suíte de testes (encontrados na impl. 018)]]
- relates_to [[USE_TELEMETRY torna OpenTelemetry opcional]]
