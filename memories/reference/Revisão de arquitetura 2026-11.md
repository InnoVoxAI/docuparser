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
