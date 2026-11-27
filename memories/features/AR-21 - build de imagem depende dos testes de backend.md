---
title: AR-21 - build de imagem depende dos testes de backend
type: note
permalink: docuparser/features/ar-21-build-de-imagem-depende-dos-testes-de-backend
tags:
- ci
- github-actions
- deploy
- ar-21
---

## O que mudou (2026-11-27, 6ª sessão; branch `ci/ar-21-build-needs-tests`)

- `.github/workflows/backend-ci.yaml` também é **reutilizável** (`on: workflow_call`). O push agora só dispara em `dev`, e o PR continua igual.
- `.github/workflows/ci.yaml` (push em main/staging): o job `backend-tests` chama o backend-ci, e o `pre-deploy` tem `needs: backend-tests`. O build e o deploy usam o mesmo commit que foi testado.
- **Válvula de escape:** `workflow_dispatch` no `ci.yaml` com `skip_tests` (boolean, padrão false). O `pre-deploy` só roda em `refs/heads/main` ou `refs/heads/staging`, porque o disparo manual aceita qualquer branch.

## Armadilhas que o desenho evita
- [gotcha] O skip de um job ancestral se propaga: com `backend-tests` "skipped", o `success()` padrão pularia todos os deploys. Por isso `pre-deploy` e `deploy-*` têm `if: ${{ !cancelled() && needs.<anterior>.result == 'success' }}`. #github-actions
- [gotcha] Num workflow chamado, `github.workflow` é o nome do **chamador**. O grupo de concorrência do backend-ci virou `backend-ci-${{ github.workflow }}-${{ github.ref }}`, para o run do PR/dev e o run dentro do CI não se cancelarem. #github-actions
- [decision] Opção escolhida pelo usuário entre `workflow_call` + `needs`, `workflow_run`, fundir os arquivos e só branch protection: `workflow_call`, com a válvula `skip_tests` por dispatch.

## Validação
YAML validado com pyyaml. actionlint não rodou (bloqueado no container). O Backend CI ainda não tinha passado no runner. O PR do AR-21 o dispara (mexe em `backend-ci.yaml`): só mergear com ele verde.

## Relações
- depends_on [[AR-20 - CI de backend]]
- part_of [[Revisão de arquitetura 2026-11]]
