---
title: AR-14 - Diretórios e arquivos sem uso
type: note
permalink: docuparser/decisions/ar-14-diretorios-e-arquivos-sem-uso
tags:
- architecture-review
- ar-14
- cleanup
---

# AR-14 - Diretórios e arquivos sem uso

Revisão de arquitetura 2026-11, fase 1. Branch `chore/ar-14-unused-files` @ 8344c41b, a partir de `dev` (2026-11-27). Com ela, a fase 1 fica encerrada no código.

## Observações
- [decision] `camunda-workers/` e `layout-service/` apagados do disco: só tinham `.pyc` e nunca foram versionados #cleanup
- [decision] `backend-core/not-used-with-s3/` FICA: é a saída do `approved_exporter` nos testes locais. O `/docuparser/.env` define `DOCUPARSE_APPROVED_EXPORT_DIR=not-used-with-s3` (caminho relativo), e o diretório está no `.gitignore`. Não apagar #gotcha
- [decision] `/docuparser/scripts/` removido inteiro (experimentos de OCR: OLMOCR e o seu docker-compose, OpenRouter, DeepSeek, Tesseract, notebooks). Ninguém o referenciava. O histórico continua no git
- [decision] O `pyproject.toml` da raiz ficou sem dependências. O arquivo e o `project.version` NÃO podem sair: o `ci.yaml` lê a tag da imagem dali (pyproject-info) e o arquivo está no filtro de paths do push #gotcha
- [fact] `tests/load/simulate_module_load.py` foi consertado: o backend-com é flat (`import config`, `from services...`). Roda no venv do com: `cd backend-com && uv run --frozen --all-extras python ../tests/load/simulate_module_load.py`
- [fact] O volume `docuparse-events` continua no compose até o D-04 (publish no barramento) ser decidido
- [fact] As 8 E402 do simulador já existiam (o `sys.path` vem antes dos imports). O pre-commit não cobre `docuparse-project/tests/`

## Relações
- part_of [[Revisão de arquitetura 2026-11]]
- follows [[AR-12 - Contratos e leitura mortos do barramento de eventos]]
