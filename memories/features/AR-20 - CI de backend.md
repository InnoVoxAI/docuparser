---
title: AR-20 - CI de backend
type: note
permalink: docuparser/features/ar-20-ci-de-backend
tags:
- ci
- testes
- revisao-arquitetura
---

# AR-20 - CI de backend

Branch `ci/ar-20-backend-ci` (commit bc2a9c4b, a partir de `dev`), 2026-11-27. Ainda não rodou no GitHub.

- [workflow] `.github/workflows/backend-ci.yaml`: `lint` (ruff 0.17.6 em backend-core, backend-com, backend-ocr, langextract-service, shared e contracts), `test-core` (Postgres 16 como service, `makemigrations --check --dry-run`, pytest do core, testes de shared e contracts com o venv do core) e `test-services` (matriz com com, ocr e langextract, `uv sync --frozen --all-extras`).
- [fato] `shared/` e `contracts/` não têm pyproject. Os testes deles rodam com o venv do backend-core e `-p no:django`.
- [fato] `docuparse-project/tests/load/` fica fora do lint de propósito (E402 em script de carga).
- [decisao] `ruff.toml`: migrations ignoram I001, para o autofix não alterar migrations que já rodaram (guardrail do CLAUDE.md).
- [bug-teste] backend-com: o TestClient do Starlette 1.x procura `httpx2` e, sem ele, usa o `httpx`, que está só no extra `test`. Por isso o CI instala os extras. Duas asserções estavam desatualizadas: `duplicate_count` (só no webhook de e-mail, **não** no do WhatsApp) e a senha IMAP, que vem do EmailSettings.
- [bug-teste] backend-ocr: os testes faziam monkeypatch de `FieldExtractor`, que foi removido. `legacy_extraction` é no-op hoje. Os testes que leem `/docuparser/docs_teste/` (não versionado) agora pulam quando o arquivo falta.
- [pendente] A simulação em ambiente limpo (sem o `.env`) foi interrompida por um reinício da máquina. O primeiro run do PR valida o workflow. Risco principal: o job do core depender de env vars que só o `.env` local define.

Relacionado: [[Revisão de arquitetura 2026-11]], [[Bugs pré-existentes na suíte de testes (encontrados na impl. 018)]]
