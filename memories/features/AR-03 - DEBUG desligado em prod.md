---
title: AR-03 - DEBUG desligado em prod
type: note
permalink: docuparser/features/ar-03-debug-desligado-em-prod
tags:
- architecture-review
- AR-03
- settings
- k8s
---

# AR-03 - DEBUG desligado em prod

Estado em 2026-11-27: código em `fix/ar-03-debug-bool` @ dda55d1c (sem PR); repo k8s em
`chore/docuparser-debug-off` @ ceebf26 (a partir de `origin/main`, sem push).

## Observations
- [bug] `DEBUG = os.environ.get("DEBUG", True)` tratava "False" como verdadeiro e ligava o DEBUG sem a variável #settings
- [fix] `core/env.py:env_flag(name, default=False)`: só `1/true/yes/on` ligam; `DEBUG = env_flag("DEBUG", default=False)` #settings
- [test] `backend-core/core/tests/test_debug_setting.py` importa o `core.settings` real num subprocesso #test
- [deploy] ConfigMap hml e prod com `DEBUG: "False"` só tem efeito numa imagem com o fix; na 0.0.15 nada muda #k8s
- [deploy] Ordem: fix em `dev` antes da próxima tag, para a tag do AR-04 trazer o AR-03; depois merge das branches k8s com a tag em hml e smoke #k8s
- [finding] Nada depende de DEBUG=True: `ALLOWED_HOSTS=["*"]`, CORS pela env, API com JWT (sem CSRF), front lê só `detail`/`error.code`, download via `FileResponse`, sem `MEDIA_*` #settings
- [finding] Só o CSS do `/admin/` dependia de DEBUG=True (runserver da 0.0.15). Sob gunicorn some de qualquer jeito; virou o AR-07 #admin
- [finding] `/admin/` exposto em prod (login 200 em 2026-11-27), nenhum modelo registrado; login provavelmente falha por CSRF atrás do Traefik (sem `SECURE_PROXY_SSL_HEADER`/`CSRF_TRUSTED_ORIGINS`) #admin
- [finding] A ConfigMap `docuparser-config` é compartilhada pelos 4 deployments, mas só o core lê `DEBUG` #k8s

## Relations
- part_of [[Revisão de arquitetura 2026-11]]
- depends_on [[AR-04 - gunicorn e modo release no backend-core]]
