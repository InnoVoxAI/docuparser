---
title: AR-04 - gunicorn e modo release no backend-core
type: note
permalink: docuparser/decisions/ar-04-gunicorn-e-modo-release-no-backend-core
tags:
- deploy
- backend-core
- revisao-arquitetura
- gunicorn
- migrations
---

# AR-04 - gunicorn e modo release no backend-core

Branch `chore/ar-04-gunicorn` (commit dcef9f9d, a partir de `dev`), 2026-11-27.

## O que mudou
- [imagem] `ENTRYPOINT ["sh", "/app/entrypoint.sh"]` com `CMD ["web"]`. Modos: `web` (gunicorn), `release` (`migrate_schemas --shared`, `migrate_schemas`, `seed_data`) ou qualquer outro comando, que é executado direto.
- [gunicorn] `core.wsgi:application`, gthread, **1 worker**, `GUNICORN_THREADS` (4), `GUNICORN_TIMEOUT` (120). Flags extras via `GUNICORN_CMD_ARGS` (no compose: `--reload`).
- [compose] Serviço `backend-core-release`, que reaproveita build, volumes e environment do `backend-core` via âncoras YAML. O `backend-core` espera ele terminar (`service_completed_successfully`) e roda com `DOCUPARSE_MIGRATE_ON_BOOT=false`.

## Decisões
- [decisao] 1 worker até a fila durável: cada worker do gunicorn criaria o próprio `ThreadPoolExecutor` de processamento.
- [decisao] `DOCUPARSE_MIGRATE_ON_BOOT` vem **true** por padrão. Motivo: o `deploy.yaml` grava a tag nova no repo k8s sozinho em push para main/staging, e o k8s ainda não tem initContainer. Com o padrão false, prod subiria sem migrations. #deploy
- [pendente] No repo k8s: initContainer (ou Job) com `args: ["release"]` e `DOCUPARSE_MIGRATE_ON_BOOT=false` no container web. Pedir confirmação ao usuário antes.

## Fatos corrigidos da revisão
- [fato] O `entrypoint.sh` antigo **não era usado** por nada: compose e k8s executavam o CMD do Dockerfile.
- [fato] Com django-tenants, `manage.py migrate` **é** o `migrate_schemas` (public + tenants). A tasks.md dizia "só public", o que estava errado.

## Armadilhas
- [compose] `extends` no Compose v2.40 herda o `depends_on`, o que criava um ciclo (o release dependendo de si mesmo). `!reset` e `!override` resolvem, mas o hook `check-yaml` do pre-commit recusa essas tags. Por isso as âncoras YAML.
- [compose] `docker compose config` precisa de `docuparse-project/.env` (o `env_file`) e de `-p` em minúsculas, porque o `.env` da raiz define um nome de projeto com maiúsculas.
- [admin] O `/admin/` do Django fica sem CSS no gunicorn: não há `STATIC_ROOT` nem whitenoise.

Relacionado: [[Revisão de arquitetura 2026-11]], [[Bug conhecido: threads de fundo perdem a conexão quando o Postgres reinicia]]
