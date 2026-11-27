---
title: AR-12 - Contratos e leitura mortos do barramento de eventos
type: note
permalink: docuparser/decisions/ar-12-contratos-e-leitura-mortos-do-barramento-de-eventos
tags:
- architecture-review
- event-bus
- contracts
- ar-12
---

# AR-12: contratos e leitura mortos do barramento de eventos

Estado em 2026-11-27: em `chore/ar-12-dead-contracts` @ a51fd3ea (a partir de `dev`, commitado; o usuário abre o PR).

## Fatos
- [fato] Saíram de `contracts/events` os eventos `ocr.completed`, `ocr.failed`, `layout.classified` e `extraction.completed` (`OCRCompletedEvent`, `OCRFailedEvent`, `LayoutClassifiedEvent`, `ExtractionCompletedEvent`), junto com o `examples/ocr.completed.json`. #contracts
- [fato] `contracts/` é um pacote Python interno, sem schema exportado. Nenhum cliente externo nem o frontend dependem dele.
- [fato] Saíram `shared/consume_fake_event.py` e `shared/publish_fake_event.py`.
- [fato] O Protocol `EventBus` só tem `publish`. O `RedisStreamEventBus` não lê mais nada (saíram `consume`, `consume_entries`, `latest_id` e `_field`). Para inspecionar as streams, use `XRANGE` no redis-cli. #event-bus
- [fato] O `simulate_module_load.py` já estava quebrado em `dev`: importa `backend_com` de `backend-com/src`, mas o com é flat. Ficou para o AR-14 (consertar ou apagar).
- [fato] Os testes do backend-com falham com 401 quando rodados pelo `run_script.sh`, porque o `.env` ativa a autenticação. Sem o `.env`, como no CI, passam (22).

## Decisões (escolhidas pelo usuário)
- [decisão] Tirar a leitura só do Redis e do Protocol. O `LocalJsonlEventBus` **mantém** `consume`/`consume_entries` como helper de teste: uns 15 testes do com, do core e do shared conferem com ele os eventos publicados. Não remover sem trocar esses testes por outro helper.
- [decisão] Saíram do `tests/load/simulate_module_load.py` os cenários `ocr_mock`, `layout_mock` e `langextract_mock`, que só publicavam os eventos removidos.

## Testes
- [teste] contracts: 12 passed; shared: 72 passed; com: 22 passed; core (os 4 arquivos que importam eventos): 124 passed; ruff ok.

## Relações
- continua [[AR-10 - Redis fora do ocr e do langextract e MAXLEN nas streams]]
- parte_de [[Revisão de arquitetura 2026-11]]
- relacionado [[Remoção do pipeline por eventos e do Camunda]]
