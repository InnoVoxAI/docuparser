---
title: Revisão de arquitetura 2026-11
type: note
permalink: docuparser/reference/revisao-de-arquitetura-2026-11
tags:
- arquitetura
- revisao
- roadmap
---

## Onde está

`docs/architecture-review-2026-11/`: achados, arquitetura-alvo, roadmap, backlog (AR-xx),
decisões pendentes (D-01..D-07), handoff e work_in_progress. Feita em 2026-11-26 sobre
`dev` @ `36e5fd96`, logo após a remoção do pipeline por eventos. Nenhum código foi alterado.

## Conclusões

- O formato (monólito modular Django + adaptadores sem estado) está certo. Não quebrar o
  core em microserviços nem voltar a usar barramento ou motor de workflow.
- Principal fraqueza: o processamento roda num ThreadPool em memória. Perde trabalho em
  restart, os retries cobram o OCR de novo e não escala além de 1 réplica.
  Recomendação: fila durável em Postgres (D-01).
- S1 de prod: `runserver` e `DEBUG=True` em prod, probes comentadas, CI sem testes de
  backend, `POST /api/ocr/process` sem autenticação, token interno aberto quando ausente,
  entrega com → core de 2 s sem retry.
- Sobra: o langextract como serviço separado (fundir no backend-ocr, D-02) e o Redis
  servindo só de barramento sem leitor.

Relacionado: [[Remoção do pipeline por eventos e do Camunda]],
[[Bug conhecido: threads de fundo perdem a conexão quando o Postgres reinicia]].

## Implementação (2026-11-27)

AR-01, AR-02, AR-04 (imagem e compose) e AR-20 estão em `dev` (PRs #67, #68, #69, #71). AR-24 (despacho do ERP com `_with_fresh_connection`; o langextract já tinha) está mergeado em `dev` local, sem push. AR-25 (remoção de `start_document_ocr_thread`, `_run_ocr_safely` e imports órfãos em `ocr_processor.py`) está na branch local `chore/ar-25-remove-ocr-thread`, sem PR. O usuário pediu **uma AR-* por sessão**, não fases inteiras. Estado e próximos passos: seção "Próxima sessão" do `handoff.md` e `work_in_progress.md`. Decisões tomadas pelo usuário: D-01 = fila em Postgres, D-02 = fundir o langextract no backend-ocr, D-03 = retry agora e bytes ao core depois, D-06 = ignorar.

Notas: [[AR-01 - rota POST /api/ocr/process removida]], [[AR-02 - token interno falha fechado fora de dev]], [[AR-04 - gunicorn e modo release no backend-core]], [[AR-20 - CI de backend]].

## Atualização (2026-11-27, 5ª sessão)

AR-24, AR-25 (#72), AR-03 no código (#73) e AR-07 (#75, `/admin/` removido) já estão em `dev`. AR-23: o output `SKIP` do job `pre-deploy` em `.github/workflows/ci.yaml` apontava para um step `check_version` que não existe mais e ninguém o lia. A linha foi removida na branch `ci/ar-23-remove-skip-output`, sem efeito no deploy. Falta no repo k8s (perguntar antes): o deploy conjunto de AR-03 e AR-04 (ConfigMap `DEBUG: "False"` e initContainer `release`), que só funciona com uma tag gerada depois desses merges, e o AR-05.

## Atualização (2026-11-27, 6ª sessão)

AR-21 em `ci/ar-21-build-needs-tests`, a partir de `dev` e commitado (o usuário abre o PR). O `ci.yaml` chama o `backend-ci.yaml` via `workflow_call`, e o build e o deploy só rodam com os testes verdes. Em emergência, `workflow_dispatch` com `skip_tests`. AR-23 já em `dev` (#76). Próxima: AR-26. Ver [[AR-21 - build de imagem depende dos testes de backend]].

- [progresso] 2026-11-27: AR-27 (retry classificado) commitado em `fix/ar-27-retry-classificado`. Ver [[Retry classificado no orquestrador (AR-27)]].
- [progresso] 2026-11-27: AR-27 já em `dev` (#79). AR-10 commitado em `chore/ar-10-redis-ocr-langextract` (k8s em `chore/docuparser-events-config`, sem push). Ver [[AR-10 - Redis fora do ocr e do langextract e MAXLEN nas streams]]. Próxima: AR-11.
