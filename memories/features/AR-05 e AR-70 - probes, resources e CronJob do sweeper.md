---
title: AR-05 e AR-70 - probes, resources e CronJob do sweeper
type: note
permalink: docuparser/features/ar-05-e-ar-70-probes-resources-e-cron-job-do-sweeper
tags:
- k8s
- probes
- cronjob
- revisao-arquitetura
---

Feito em 2026-11-27 (14ª sessão). Código e CI já em `dev` (#88 e #89); as branches k8s aguardam o deploy final.

## Branches
- `fix/ar-05-blocking-routes` (repo principal, #88): rotas de trabalho do ocr (`/api/v1/process`), do langextract (`/api/v1/extract`) e de ingestão e poll do com rodam com `run_in_threadpool`. Antes, eram `async def` com I/O bloqueante (OpenRouter/LLM com até 120–300 s, imaplib, urllib, boto3): o event loop parava, o `/health` não respondia e a liveness mataria o pod no meio de um OCR pago. Há um teste por serviço (`test_health_responds_while_*_blocks`).
- `ci/ar-70-cronjob-image-tag` (repo principal, #89): o sed e o `git add` do `deploy.yaml` valem para `docuparser-<svc>/*.yaml`, não só para o `deployment.yaml`.
- `chore/docuparser-probes-resources` (repo k8s, **empilhada em `chore/docuparser-core-release`**).
- `chore/docuparser-sweep-cronjob` (repo k8s): `docuparser-core/cronjob.yaml` em hml e prod.

## Fatos
- [endpoint] Health do core: `/api/ocr/health` e `/api/ocr/ready`. Na raiz, `/health` dá 404. Os quatro serviços têm health estático, sem autenticação. `ALLOWED_HOSTS=["*"]`.
- [decisao] Resources: só request de CPU e limite de memória, sem limite de CPU (padrão do cortex). core e init 100m/384Mi→1Gi, com 50m/128Mi→512Mi, ocr 100m/256Mi→1536Mi, langextract 50m/128Mi→512Mi, CronJob 50m/256Mi→512Mi. São estimativas: não havia como medir (sem kubectl no dev container).
- [decisao] Probes: liveness 20 s/5 s/3, readiness 10 s/3 s/3, startupProbe só no core (5 s × 36).
- [decisao] CronJob: `*/10`, Forbid, backoffLimit 0, activeDeadlineSeconds 300, startingDeadlineSeconds 300, `--older-than-minutes 30`, em hml e prod.
- [armadilha] O sed do CI só roda no build. Branches k8s mergeadas depois da tag chegam com `image: ...:0.0.15` no initContainer e no CronJob. O `args: ["release"]` quebra na 0.0.15, que não tem ENTRYPOINT. Antes do merge, troque a tag nessas linhas.
- [regra] Rotas `async def` nos serviços FastAPI não chamam I/O bloqueante direto: use `await run_in_threadpool(...)`.

## Relações
- part_of [[Revisão de arquitetura 2026-11]]
- relates_to [[AR-04 - gunicorn e modo release no backend-core]]
