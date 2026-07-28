---
description: "Task list for Fase B — Download e organização dos arquivos"
---

# Tasks: Fase B — Download e organização dos arquivos

**Input**: Design documents from `docs/specs/013-file-download-organization/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (relatorio-final, fase-b-erros, cli-and-config)

**Tests**: INCLUÍDOS. A constituição do projeto (Testing Standards) exige unit tests **sem rede/disco** para a lógica de negócio e cobertura ≥80%. Logo, cada história traz suas tarefas de teste.

**Depende de**: spec 012 (Fase A). A interface é o arquivo `mapa_download.csv` (contrato 012). Reusa `superlogica_download_map.sanitize`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência de tarefa incompleta)
- **[Story]**: US1–US5 (mapeia as histórias do spec.md)
- Todos os caminhos são relativos à raiz do repositório.

**Raiz do pacote**: `docuparse-project/scripts/SELECT/superlogica_file_downloader/` (abreviada abaixo como `PKG/`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: esqueleto do pacote rastreável, irmão da Fase A.

- [X] T001 Criar a estrutura do pacote em `PKG/`: `__init__.py` e `__main__.py` (entrypoint `python -m superlogica_file_downloader` chamando `cli.app`).
- [X] T002 [P] Criar `PKG/tests/conftest.py` que adiciona `docuparse-project/scripts/SELECT/` ao `sys.path` (permite importar `superlogica_file_downloader` e `superlogica_download_map`), espelhando o conftest da Fase A.
- [X] T003 [P] Confirmar que **nenhuma dependência nova** é necessária (só `requests`/`Typer` já em `pyproject.toml`) e que a config de `ruff`/`pytest` do repo cobre `PKG/`; ajustar apenas se o novo caminho exigir (sem editar dependências).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: config, leitura do mapa e esqueleto de CLI/pipeline — pré-requisito de TODAS as histórias.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase.

- [X] T004 Implementar `PKG/config.py`: `Config` (frozen dataclass) + `build_config(work_dir, ...)` resolvendo caminhos relativos ao `work_dir` (mapa, downloads-root, final-csv, errors), com constantes no topo — `HTTP_PAUSE_S=1.0`, `HTTP_TIMEOUT_S=30.0`, `HTTP_RETRIES=3`, `HTTP_BACKOFF_BASE_S=2.0`, `PDF_SIGNATURE=b"%PDF"`, `FINAL_COLUMNS`. Ver `contracts/cli-and-config.md` e `data-model.md §6`.
- [X] T005 [P] Implementar `PKG/map_io.py` (parte 1 — leitura): `MapRow` dataclass (colunas do contrato 012) + `load_map(path, fmt)` que lê csv/json e **valida colunas essenciais** (`url_download`, `nome_arquivo`, `pasta_destino`, `status`); ausência/ilegibilidade ou colunas faltando → exceção fatal (E-01). Trata as colunas de conteúdo como somente leitura (FR-004).
- [X] T006 Implementar `PKG/cli.py` (esqueleto) + wiring do `__main__`: Typer app com flags `--work-dir --map --map-format --downloads-root --final-csv --errors --pause --timeout --retries --verbose` (ver `contracts/cli-and-config.md`); códigos de saída 0/1/2; chama um `pipeline.run(config)` ainda mínimo.

**Checkpoint**: config + leitura de mapa + CLI prontos — histórias podem começar.

---

## Phase 3: User Story 1 - Baixar e organizar os arquivos do mapa (Priority: P1) 🎯 MVP

**Goal**: para cada linha pendente, baixar via GET público e salvar em `downloads/<pasta_destino>/<nome_arquivo>`, criando diretórios (inclusive `_A_Revisar`).

**Independent Test**: dado um mapa com N linhas pendentes de URLs válidas (mockadas), N arquivos aparecem nos caminhos corretos.

### Tests for User Story 1

- [X] T007 [P] [US1] `PKG/tests/test_map_io.py`: carga OK; colunas essenciais faltando → fatal (E-01); `url_download` vazia/malformada numa linha é detectável (E-02).
- [X] T008 [P] [US1] `PKG/tests/test_downloader.py` (básico): GET de sucesso com sessão **mockada** retorna os bytes; `url_download` vazia/malformada → erro sem requisição (E-02).

### Implementation for User Story 1

- [X] T009 [P] [US1] Implementar `PKG/naming.py` (parte 1 — nome base): `resolve_name(row)` = `sanitize(nome_arquivo)` (reuso de `superlogica_download_map.sanitize`) + garantia de extensão `.pdf`; se `nome_arquivo` vazio → fallback determinístico `{fornecedor_sanitizado}_{id_da_url}.pdf`. `dest_dir(config, row)` = `downloads/<sanitize(pasta_destino)>/` (E-07).
- [X] T010 [US1] Implementar `PKG/downloader.py` (parte 1 — GET): `fetch_file(url, config, *, session)` com `requests.Session`, `stream=True`, `timeout`; devolve status/head/bytes-iter. Sem retry ainda (adicionado em US5).
- [X] T011 [US1] Implementar `PKG/atomic.py`: `save_atomic(dest_path, byte_source)` grava em `<dest>.part` no mesmo diretório (cria dirs) e faz `os.replace` para o nome final; remove `.part` em falha (E-11).
- [X] T012 [US1] Implementar `PKG/pipeline.py` (parte 1 — fluxo feliz): iterar linhas pendentes → `dest_dir`/`resolve_name` → `fetch_file` → `save_atomic`; wire no `cli.py`; resumo mínimo (total/baixadas). Cria `_A_Revisar` naturalmente via `dest_dir`.

**Checkpoint**: US1 funcional — baixa e organiza arquivos de URLs válidas.

---

## Phase 4: User Story 2 - Nunca salvar corrompido, truncado ou sobrescrito (Priority: P1)

**Goal**: só gravar o arquivo esperado e completo; rejeitar conteúdo inválido, garantir atomicidade e anti-colisão determinística sem sobrescrever.

**Independent Test**: (a) 200 com HTML → nada salvo, linha erro; (b) conexão cai no meio → sem arquivo final truncado; (c) mesmo nome em pasta → nome alternativo determinístico, original intacto.

### Tests for User Story 2

- [X] T013 [P] [US2] `PKG/tests/test_content.py`: `looks_like_pdf(b"%PDF-1.7...")` True; HTML/`text/html` → False (E-05).
- [X] T014 [P] [US2] `PKG/tests/test_naming.py`: colisão gera `{id}_{nome}` **determinístico** (mesma linha → mesmo nome em 2 execuções); nunca igual ao existente (E-06).
- [X] T015 [P] [US2] `PKG/tests/test_atomic.py` (usa `tmp_path`): falha durante a escrita não deixa arquivo com nome final; `.part` é removido (E-11).

### Implementation for User Story 2

- [X] T016 [P] [US2] Implementar `PKG/content.py`: `looks_like_pdf(head: bytes)` (assinatura `%PDF`) + checagem de `Content-Type`; `validate_content(head, content_type, config)` → ok/motivo (E-05).
- [X] T017 [US2] `PKG/naming.py` (parte 2 — anti-colisão): `final_path(dest_dir, base_name, row)` — se o destino já existe, prefixar com o `id` da `url_download` → `{id}_{base_name}`; determinístico; nunca sobrescrever; anomalia (colisão com outra url) → sinalizar erro (E-06). Ver `research.md D1`.
- [X] T018 [US2] `PKG/atomic.py` (parte 2): promover o `.part` ao nome final **somente após** validação de conteúdo (D2); integrar a validação no `save_atomic`/pipeline.
- [X] T019 [US2] `PKG/pipeline.py` (parte 2): após o download, validar conteúdo (T016) antes de promover; conteúdo inválido → nada salvo, linha vira erro (E-05); aplicar `final_path` anti-colisão (T017).

**Checkpoint**: US1+US2 — arquivos salvos são íntegros, atômicos e não colidem.

---

## Phase 5: User Story 3 - CSV final incremental (entregável central) (Priority: P1)

**Goal**: cada sucesso vira imediatamente uma linha no `relatorio_final.csv` (nome salvo, hyperlink de origem, categoria, caminho local; +pasta/fornecedor).

**Independent Test**: baixar algumas linhas, interromper, e o CSV final já contém exatamente as concluídas, cada uma uma vez.

### Tests for User Story 3

- [X] T020 [P] [US3] `PKG/tests/test_outputs_finalcsv.py`: append incremental grava header uma vez + linha por sucesso; `url_download` repetida não é regravada (dedup — RN-6); colunas conforme `contracts/relatorio-final.md`.

### Implementation for User Story 3

- [X] T021 [US3] Implementar `PKG/outputs.py` (parte 1 — CSV final): `FinalCsvWriter` (context manager) com append+flush por linha, carga das `url_download` já presentes (dedup), colunas `nome_arquivo,hyperlink_origem,categoria,caminho_local,pasta_destino,fornecedor`.
- [X] T022 [US3] `PKG/pipeline.py` (parte 3): após cada `save_atomic` bem-sucedido, appendar imediatamente a `FinalRow` (RN-5); `caminho_local` relativo ao work-dir (FR-015).

**Checkpoint**: US1+US2+US3 — entregável central produzido incrementalmente.

---

## Phase 6: User Story 4 - Execução interrompível e retomável (Priority: P1)

**Goal**: ao retomar, pular o já concluído (status `baixado` + arquivo presente) e processar só o que falta, sem rebaixar nem duplicar.

**Independent Test**: rodar parte, interromper, rodar de novo → nada rebaixado, sem duplicatas no CSV final.

### Tests for User Story 4

- [X] T023 [P] [US4] `PKG/tests/test_resume.py`: pular quando `status=baixado` **e** arquivo existe; rebaixar quando arquivo sumiu; linha `erro` é re-tentada; nenhuma duplicata no CSV final (RN-4/RN-6/E-12).

### Implementation for User Story 4

- [X] T024 [US4] `PKG/map_io.py` (parte 2 — status): `update_status(map_path, fmt, url_download, status)` reescrevendo o mapa via arquivo temporário + `os.replace`, preservando todas as demais colunas (FR-004); flush frequente para consistência sob interrupção (D7).
- [X] T025 [US4] `PKG/pipeline.py` (parte 4 — retomada): `should_skip(row, final_path)` = `status==baixado` **E** arquivo presente no caminho determinístico; carregar conjunto concluído do CSV final; transições `pendente→baixado/erro`; `erro` re-tentado (D6).

**Checkpoint**: US1–US4 — execução retomável e idempotente.

---

## Phase 7: User Story 5 - Resiliência, relatório de erros e sinal de expiração (Priority: P2)

**Goal**: fail-soft; retry/backoff/pausa; relatório de erros; sinalizar provável expiração (E-04).

**Independent Test**: simular erros HTTP (incl. expiração) e rate limiting → execução continua, falhas no relatório com motivo/tentativas, expiração destacada.

### Tests for User Story 5

- [X] T026 [P] [US5] `PKG/tests/test_downloader_retry.py`: retry com backoff (sleep **injetado**, sem dormir); status não-repetíveis `{400,401,403,404,410}` abortam cedo; esgotamento → erro com nº de tentativas (E-03/E-10).
- [X] T027 [P] [US5] `PKG/tests/test_expiration.py`: `detect_expiration(status, content_type, head)` → True em 401/403/410 e em 200-HTML com marcadores de sessão; False caso contrário (E-04).

### Implementation for User Story 5

- [X] T028 [US5] `PKG/downloader.py` (parte 2 — resiliência): retry com backoff progressivo + pausa entre requisições + sleep injetável; `_NO_RETRY_STATUS`; devolve `DownloadOutcome` (ok/motivo/tentativas/possivel_expiracao) (E-03/E-09/E-10).
- [X] T029 [P] [US5] `PKG/content.py` (parte 2): `detect_expiration(...)` (padrão E-04) usado pelo downloader/pipeline para marcar `possivel_expiracao`.
- [X] T030 [US5] `PKG/outputs.py` (parte 2 — erros): `ErrorReportWriter` para `fase_b_erros.csv` com colunas `url_download,motivo,tentativas,possivel_expiracao,nome_arquivo,pdf_origem` (ver `contracts/fase-b-erros.md`).
- [X] T031 [US5] `PKG/pipeline.py` (parte 5 — fail-soft + fatal): registrar cada falha definitiva no relatório e continuar; falha de escrita generalizada (permissão/espaço) → fatal, pontual → erro (E-08); marcar `status=erro`.

**Checkpoint**: US1–US5 — resiliente, observável, com caminho de recuperação por expiração.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T032 [US5] `PKG/pipeline.py` (resumo final, FR-022): imprimir total, baixadas, puladas, erros por tipo, onde ficaram as saídas; **destacar** recomendação de re-rodar a Fase A quando houver erros de possível expiração (E-04).
- [X] T033 [P] Criar `PKG/README.md` (uso, retomada, fluxo de expiração) alinhado ao `quickstart.md`.
- [X] T034 Segurança: confirmar **zero** imports de Google/OAuth/Drive e de PyMuPDF/BeautifulSoup no pacote (SC-007); revisar sanitização contra path traversal em `pasta_destino`/`nome_arquivo`.
- [X] T035 Rodar `uvx ruff check superlogica_file_downloader` (zero violações) e `uv run pytest superlogica_file_downloader/tests` (cobertura ≥80% da lógica de negócio).
- [X] T036 Validar o `quickstart.md` de ponta a ponta (execução + retomada) e ajustar defaults se necessário.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — **bloqueia** todas as histórias.
- **User Stories (Phase 3–7)**: dependem da Foundational.
  - Ordem de valor recomendada (todas P1 exceto US5): US1 → US2 → US3 → US4 → US5.
  - US2/US3 podem ser paralelizadas após US1 (arquivos distintos: `content.py`/`outputs.py`), mas ambas tocam `pipeline.py` na integração → integrar em série.
- **Polish (Phase 8)**: depende das histórias desejadas.

### User Story Dependencies

- **US1 (P1)**: base — habilita todas. Requer Foundational.
- **US2 (P1)**: estende o fluxo de US1 (validação/atômico/anti-colisão).
- **US3 (P1)**: consome o resultado de US1; `outputs.py` é independente, integra no `pipeline.py`.
- **US4 (P1)**: precisa de US1 (nome determinístico) e US3 (dedup do CSV) para a retomada completa.
- **US5 (P2)**: estende `downloader.py`/`pipeline.py` de US1; independentemente testável (mock).

### Within Each User Story

- Testes antes da implementação (devem falhar primeiro).
- `naming`/`content`/`outputs` (arquivos próprios) antes da integração no `pipeline.py`.
- `pipeline.py` é ponto de integração comum → nunca paralelizar tarefas que o editam.

### Parallel Opportunities

- Setup: T002, T003 em paralelo.
- Foundational: T005 [P] paralelo a T004; T006 depois (usa ambos).
- Testes marcados [P] de uma história rodam juntos (arquivos distintos).
- `content.py` (T016) e `outputs.py` (T021) podem avançar em paralelo entre US2/US3.

---

## Parallel Example: User Story 1

```bash
# Testes de US1 juntos (arquivos distintos):
Task: "PKG/tests/test_map_io.py — carga + colunas faltando fatal (E-01)"
Task: "PKG/tests/test_downloader.py — GET de sucesso com sessão mockada"

# Implementação inicial em paralelo (arquivos distintos):
Task: "PKG/naming.py — resolve_name + dest_dir + fallback"
# (downloader/atomic/pipeline seguem em série pela integração no pipeline)
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup → 2. Phase 2 Foundational → 3. Phase 3 US1.
4. **STOP e VALIDE**: US1 baixa e organiza arquivos de URLs válidas.

### Incremental Delivery

1. Setup + Foundational → fundação pronta.
2. + US1 (MVP: baixa/organiza) → validar.
3. + US2 (integridade) → validar.
4. + US3 (CSV final) → validar (entregável).
5. + US4 (retomada) → validar idempotência.
6. + US5 (resiliência/erros/expiração) → validar fail-soft.
7. Polish.

---

## Notes

- [P] = arquivos diferentes, sem dependência.
- Reuso: `from superlogica_download_map.sanitize import sanitize, url_decode`. Nenhuma outra dependência da Fase A.
- **Sem** Google/OAuth/PyMuPDF/BeautifulSoup no pacote (SC-007).
- Testes de lógica pura **sem rede/disco**; `requests` mockado, sleep injetado, atômico via `tmp_path`.
- Commit após cada tarefa ou grupo lógico; parar em qualquer checkpoint para validar.
