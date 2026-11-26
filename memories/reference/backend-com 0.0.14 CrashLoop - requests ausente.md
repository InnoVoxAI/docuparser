---
title: backend-com 0.0.14 CrashLoop - requests ausente
type: note
permalink: docuparser/reference/backend-com-0.0.14-crash-loop-requests-ausente
tags:
- bug
- backend-com
- deploy
- opentelemetry
---

# backend-com 0.0.14 CrashLoop - requests ausente

- [bug] docuparser-com:0.0.14 entrou em CrashLoopBackOff em hml e prod (2026-11-26): `ModuleNotFoundError: No module named 'requests'` em `api/app.py` ao importar `opentelemetry.instrumentation.requests`.
- [causa] `opentelemetry-instrumentation-requests` NÃO depende de `requests`. O pacote vinha de forma transitiva pelas dependências do Camunda, removidas no PR #66 (d5c7c416).
- [por que passou despercebido] Localmente `requests` ainda vem pelo extra `test` (moto). A imagem instala só `--extra debounce`.
- [fix] `requests>=2.32.0` adicionado explicitamente às dependências do backend-com (release 0.0.15).
- [lição] Ao remover dependências, validar o import do app num venv com só os extras do Dockerfile (`uv sync --frozen --extra debounce`).
