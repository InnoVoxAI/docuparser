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

AR-01, AR-02, AR-04 (imagem e compose) e AR-20 estão em `dev` (PRs #67, #68, #69, #71). AR-24 (despacho do ERP com `_with_fresh_connection`; o langextract já tinha) está na branch local `fix/ar-24-erp-dispatch-fresh-connection`, sem PR. O usuário pediu **uma AR-* por sessão**, não fases inteiras. Estado e próximos passos: seção "Próxima sessão" do `handoff.md` e `work_in_progress.md`. Decisões tomadas pelo usuário: D-01 = fila em Postgres, D-02 = fundir o langextract no backend-ocr, D-03 = retry agora e bytes ao core depois, D-06 = ignorar.

Notas: [[AR-01 - rota POST /api/ocr/process removida]], [[AR-02 - token interno falha fechado fora de dev]], [[AR-04 - gunicorn e modo release no backend-core]], [[AR-20 - CI de backend]].
