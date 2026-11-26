# Roadmap em fases

As fases estão ordenadas por **risco reduzido por esforço**. As fases 0 e 1 não dependem de
decisões de arquitetura. As fases 2 e 3 dependem de [decisions-pending.md](decisions-pending.md).

```
Fase 0  Segurança e prod imediata ──┐
Fase 1  Limpeza de sobras + CI ─────┼─► Fase 2  Fila durável (D-01) ─► Fase 3  Fronteiras (D-02, D-03, D-07)
                                    │                                  │
                                    └─► Fase 4  Operação (métricas, alertas, backups, cron) ◄┘
Fase 5  Qualidade contínua (frontend, docs, organização do core)  — em paralelo, baixa prioridade
```

## Fase 0 — Segurança e produção imediata (1–2 dias)
Objetivo: fechar os S1 que não exigem redesenho.
- AR-01 Autenticar ou remover `POST /api/ocr/process`.
- AR-02 Token interno: falhar fechado fora de dev e remover "teste456".
- AR-03 `DEBUG=False` em prod (repo k8s).
- AR-04 Trocar `runserver` por gunicorn e tirar as migrations do CMD.
- AR-05 Reativar as probes e definir requests e limits.
- AR-06 (usuário) Rotacionar e remover os segredos versionados no repo k8s (D-06).

## Fase 1 — Limpeza e rede de segurança (2–4 dias)
Objetivo: remover sobras e impedir regressões.
- AR-10..AR-19: sobras do barramento e dos workers (env, deps, flags, contratos mortos,
  diretórios), docs desatualizados e `docs/architecture.md` reescrito.
- AR-20..AR-23: CI de backend (ruff, pytest, `makemigrations --check`), tags imutáveis e
  correção do `ci.yaml`.
- AR-24, AR-25: `_with_fresh_connection` nas threads restantes e remoção de
  `start_document_ocr_thread`.

## Fase 2 — Processamento durável (1–2 semanas) — depende de D-01
- AR-30..AR-36: fila, worker separado, idempotência por etapa, retry classificado,
  heartbeat e recuperação, Deployment do worker e testes de restart e duplo envio.
- AR-40: remover o Redis, ou rebaixá-lo a broker (D-01 e D-04).

## Fase 3 — Fronteiras de serviço (1 semana)
- AR-50..AR-53: fundir o langextract no backend-ocr (D-02).
- AR-54, AR-55: cliente OpenRouter único com rate limit, backoff para 429 e breaker.
- AR-60..AR-62: entrega durável backend-com → core (D-03).
- AR-65: unificar a responsabilidade de classificação (D-07).

## Fase 4 — Operação (3–5 dias, pode correr junto com as fases 2 e 3)
- AR-70..AR-75: CronJobs, métricas e alertas, `/ready` real, backups, NetworkPolicy,
  usuário não-root.

## Fase 5 — Qualidade contínua (backlog)
- AR-80..AR-86: refresh de token no front, lazy routes, dependências mortas, `AppLayout`,
  divisão do `documents/views.py`, renomear `backend-core/models/`, OpenAPI.
