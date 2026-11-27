---
title: AR-02 - token interno falha fechado fora de dev
type: note
permalink: docuparser/decisions/ar-02-token-interno-falha-fechado-fora-de-dev
tags:
- seguranca
- backend-core
- revisao-arquitetura
- auth
---

# AR-02 - token interno falha fechado fora de dev

Branch `fix/ar-02-internal-token-fail-closed` (commit 5453394b, a partir de `dev`), 2026-11-27.

## Comportamento de `_internal_token_error` (documents/views.py)
- [regra] Service token ou usuário com JWT: passa (como antes).
- [regra] Sem `DOCUPARSE_INTERNAL_SERVICE_TOKEN` e `INTERNAL_ENDPOINTS_OPEN_WITHOUT_TOKEN=True`: anônimo passa (comportamento histórico de dev).
- [regra] Sem token fora de dev: anônimo recebe **503** `internal service token not configured`.
- [regra] Com token e sem credencial válida: 401 `invalid internal service token` (saiu o "teste456").
- [log] `documents.startup.log_startup_config` registra ERROR no boot quando o token falta fora de dev.

## Decisões
- [decisao] O ambiente vem de `DEPLOYMENT_ENVIRONMENT`, que já existia no compose e no tracing, e não de uma variável nova `DOCUPARSE_ENV` como sugeria a tasks.md. Valores dev: development, dev, local, test. #config
- [decisao] Ambiente **ausente conta como produção**. Motivo: o k8s (hml e prod) não define `DEPLOYMENT_ENVIRONMENT` e roda com `DEBUG=True`, então nem DEBUG nem o ambiente servem para detectar prod.
- [decisao] Falha na requisição (503), e não no boot: o boot falhando derrubaria também migrations e comandos de manutenção.
- [verificado] hml e prod já têm `DOCUPARSE_INTERNAL_SERVICE_TOKEN` no Secret (conferido só pelos nomes das chaves), então o deploy não muda nada lá.

## Armadilhas encontradas
- [testes] O pytest-django carrega o settings antes do conftest ser importado. Um `os.environ.setdefault(...)` no conftest, mesmo no topo do módulo, **não** afeta o settings. Sobrescreva o setting no teste (`self.settings(...)`).
- [testes] Requisição anônima sem tenant cai no schema `public` depois do gate (`relation "documents_document" does not exist`). Para testar o caso aberto em dev, chame `_internal_token_error` direto.
- [bug] `DEBUG = os.environ.get("DEBUG", True)` em `core/settings.py` trata a string "False" como verdadeira. Corrigir junto com o AR-03.

Relacionado: [[Revisão de arquitetura 2026-11]], [[AR-01 - rota POST /api/ocr/process removida]]
