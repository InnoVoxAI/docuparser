---
title: AR-10 - Redis fora do ocr e do langextract e MAXLEN nas streams
type: note
permalink: docuparser/decisions/ar-10-redis-fora-do-ocr-e-do-langextract-e-maxlen-nas-streams
tags:
- architecture-review
- redis
- event-bus
- ar-10
---

# AR-10: Redis fora do ocr e do langextract, e MAXLEN nas streams

Estado em 2026-11-27: código em `chore/ar-10-redis-ocr-langextract` (a partir de `dev`, commitado, o usuário abre o PR). No repo k8s, `chore/docuparser-events-config` @ eae066f, sem push.

## Fatos
- [fato] Nenhum código de produção lê as streams do Redis. O único leitor é `shared/consume_fake_event.py` (script de teste, que sai no AR-12). #event-bus
- [fato] Quem publica: o backend-com (`document.received`) e o backend-core (`erp.integration.requested`, `erp.sent`, `erp.failed`). O backend-ocr e o langextract-service nunca usaram o barramento, só o `RedisInstrumentor`.
- [fato] No k8s, os 4 serviços leem a mesma ConfigMap `docuparser-config` e o mesmo Secret `docuparser-secrets` via `envFrom`.

## Decisões (escolhidas pelo usuário)
- [decisão] `xadd(..., maxlen=N, approximate=True)` com N = `DOCUPARSE_EVENT_STREAM_MAXLEN`, padrão 10000. `0` desliga o corte. Um valor inválido cai no padrão com aviso, em vez de levantar erro, porque o publish do com fica fora de try/except.
- [decisão] Separar a ConfigMap no k8s: `docuparser-events-config` (com `DOCUPARSE_EVENT_BUS` e o MAXLEN), referenciada só por core e com. O `REDIS_URL` continua no Secret compartilhado, porque agentes não editam segredos.
- [decisão] ocr e langextract perderam o `RedisInstrumentor`, as dependências `redis` e `opentelemetry-instrumentation-redis` e, no compose, as env vars do barramento e o `depends_on: redis`.

## Pendente
- Mergear o branch do k8s junto com a tag nova, no deploy final.
- O Redis some de vez no AR-40, depois do D-04 (que pode remover o publish).

Relações:
- part_of [[Revisão de arquitetura 2026-11]]
- relates_to [[Remoção do pipeline por eventos e do Camunda]]
