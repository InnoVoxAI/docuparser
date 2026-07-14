---
description: "Task list for Fase A — Extração e geração do mapa de download"
---

# Tasks: Fase A — Extração e geração do mapa de download

**Input**: Design documents from `docs/specs/012-download-map-extraction/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: **INCLUÍDOS** — a Constituição (II. Testing Standards) exige unit tests para lógica de negócio, sem rede/disco. Testes de lógica pura (split, categorização, sanitização, idempotência) e testes com mock/fixture para I/O externo.

**Organization**: Tarefas agrupadas por user story (prioridade da spec). Código-base do pacote:
`docuparse-project/scripts/SELECT/superlogica_download_map/` (rastreável). Credenciais/saídas ficam no diretório de trabalho (cwd, ignorado pelo git).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependências pendentes)
- **[Story]**: US1–US5 (mapeia às user stories da spec)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: inicialização do pacote e dependências

- [X] T001 Criar estrutura do pacote em `docuparse-project/scripts/SELECT/superlogica_download_map/` (`__init__.py`, `__main__.py`, `tests/`, `tests/fixtures/`)
- [X] T002 Adicionar dependências de runtime via uv (`google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2`, `beautifulsoup4`, `lxml`) atualizando `pyproject.toml` + `uv.lock`
- [X] T003 [P] Adicionar regras explícitas `credentials.json` e `token.json` ao `.gitignore` (defesa em profundidade, R10)
- [X] T004 [P] Configurar pytest (marcadores/rootdir) e garantir cobertura do ruff para o novo pacote em `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infraestrutura compartilhada que TODAS as user stories usam

**⚠️ CRITICAL**: nenhuma user story pode começar antes desta fase

- [X] T005 Implementar `config.py` — `DRIVE_FOLDER_IDS`+URLs, `WORK_DIR`/caminhos de saída, `MAP_FORMAT`, `DOWNLOADS_ROOT`, `FAMILY_RULES`, `Y_TOLERANCE_RATIO`, `HTTP_RETRIES`/`HTTP_BACKOFF_BASE_S`/`HTTP_PAUSE_S`, escopo `drive.readonly` (parametrizável, FR-024) em `docuparse-project/scripts/SELECT/superlogica_download_map/config.py`
- [X] T006 [P] Implementar `sanitize.py` — URL-decode, remoção/substituição de caracteres inválidos, trim/colapso de espaços, fallback para nome vazio/reservado (FR-017, 5.3) em `.../superlogica_download_map/sanitize.py`
- [X] T007 [P] Unit tests de sanitização (URL-decode, chars inválidos, vazio→fallback) em `.../superlogica_download_map/tests/test_sanitize.py`
- [X] T008 Implementar `drive_auth.py` — OAuth "Desktop app" read-only, carregar `credentials.json`, salvar/reutilizar/refresh de `token.json`; falha dura → E-01 fatal (exit 2) em `.../superlogica_download_map/drive_auth.py`
- [X] T009 Implementar `reports.py` (base) — coletor de exceções em memória + writer de `fase_a_relatorio.csv` (usado por US1/US3/US4) em `.../superlogica_download_map/reports.py`
- [X] T010 Implementar esqueleto da CLI em `cli.py` + `__main__.py` — flags Typer (`--work-dir`, `--recon`, `--recursive/--no-recursive`, `--map-format`, `--credentials`, `--verbose`), exit codes (0/1/2), carga de config, chamada de auth e despacho (recon vs execução completa) em `.../superlogica_download_map/cli.py`

**Checkpoint**: fundação pronta — autenticação, config, sanitização e coleta de exceções disponíveis.

---

## Phase 3: User Story 1 - Gerar o mapa de download completo (Priority: P1) 🎯 MVP

**Goal**: navegar os 3 saltos e produzir o `mapa_download.csv` — uma âncora → uma linha, com `url_download`, `nome_arquivo`, `fornecedor`, `hyperlink_origem`, `pdf_origem`, `status=pendente`.

**Independent Test**: para uma página com N âncoras, o mapa contém N linhas, cada uma com `url_download` e `nome_arquivo` preenchidos; linha de PDF sem hyperlink é ignorada sem erro.

### Tests for User Story 1 ⚠️

- [X] T011 [P] [US1] Unit test do parse de âncoras (href + `title` do `<img>`, url-decode, múltiplas âncoras) a partir de HTML fixture em `.../superlogica_download_map/tests/test_superlogica_parse.py`
- [X] T012 [P] [US1] Test de extração/cruzamento link↔célula em PDF sintético (fixture) em `.../superlogica_download_map/tests/test_pdf_extractor.py`

### Implementation for User Story 1

- [X] T013 [P] [US1] Implementar `drive_reader.py` — listar PDFs (recursivo, E-11) das duas pastas + obter bytes um a um (Salto 0); marco: imprimir nomes dos PDFs em `.../superlogica_download_map/drive_reader.py`
- [X] T014 [P] [US1] Implementar `superlogica.py` — GET da página `publico/arquivos?...` + parse (BeautifulSoup/lxml) de TODAS as âncoras (`href`→`url_download`, `img title`→`nome_arquivo`, url-decode) em `.../superlogica_download_map/superlogica.py`
- [X] T015 [US1] Implementar `pdf_extractor.py` — extrair anotações de link (`rect`+`uri`) + palavras com coords; localizar colunas pelo cabeçalho; cruzar por proximidade-y (tolerância de config); recuperar `fornecedor` e `hyperlink_origem`; extrair a célula "Categoria - Complemento" bruta (Salto 1, 5.2) em `.../superlogica_download_map/pdf_extractor.py`
- [X] T016 [US1] Implementar `mapa.py` — writer incremental (header 1×, append por linha) conforme `contracts/mapa-download.md`, `status=pendente`, fallback de nome ausente `{fornecedor}_{id}.pdf` (E-06) em `.../superlogica_download_map/mapa.py`
- [X] T017 [US1] Ligar o pipeline completo na `cli.py`: auth → listar/ler PDFs → por PDF extrair → por hyperlink resolver Superlógica → por âncora gravar linha (linha sem link → E-03 ignorar) (depende T013–T016)

**Checkpoint**: rodando de ponta a ponta, produz um mapa com as linhas de navegação (classificação entra na US2).

---

## Phase 4: User Story 2 - Classificar cada arquivo por categoria (Priority: P1)

**Goal**: dividir "Categoria - Complemento" e derivar `pasta_destino` determinística (variantes → mesma pasta; famílias agrupadas; fallback).

**Independent Test**: dado um conjunto de células, a divisão isola categoria/complemento corretamente (inclusive hífen sem espaço e sem separador), e variantes/famílias mapeiam para a mesma pasta.

### Tests for User Story 2 ⚠️

- [X] T018 [P] [US2] Unit tests da divisão categoria/complemento (1º ` - `, hífen sem espaço, múltiplos ` - `, sem separador, strip) em `.../superlogica_download_map/tests/test_split_categoria.py`
- [X] T019 [P] [US2] Unit tests do categorizador (chave canônica; regras de família ordenadas; fallback Title Case; `_A_Revisar`) em `.../superlogica_download_map/tests/test_categorizer.py`

### Implementation for User Story 2

- [X] T020 [P] [US2] Implementar `split_categoria_complemento()` (split no 1º ` - `, `maxsplit=1`, strip; sem separador → categoria inteira) em `.../superlogica_download_map/categorizer.py`
- [X] T021 [US2] Implementar `categorizer.py` — chave canônica (minúsculas + sem acento + pontuação→espaço + colapso), casamento por `FAMILY_RULES` (primeira que casa vence), fallback Title Case, `_A_Revisar` (Seção 6) em `.../superlogica_download_map/categorizer.py`
- [X] T022 [US2] Integrar classificação no pipeline: `pdf_extractor` usa o split; `mapa` preenche `categoria_bruta`, `complemento`, `pasta_destino` (RN-2 herança por hyperlink) (depende T015, T016, T020, T021)

**Checkpoint**: US1 + US2 = mapa completo e classificado (MVP entregável).

---

## Phase 5: User Story 3 - Rastreabilidade e rede de segurança (Priority: P1)

**Goal**: `_A_Revisar` para indeterminadas, relatório de exceções consolidado, e proveniência garantida em toda linha.

**Independent Test**: casos ambíguos/indeterminados aparecem no relatório e/ou vão a `_A_Revisar`; toda linha carrega `pdf_origem`, `hyperlink_origem` e `pasta_destino`.

### Tests for User Story 3 ⚠️

- [X] T023 [P] [US3] Unit test do fallback `_A_Revisar` + registro E-07 para categoria indeterminada em `.../superlogica_download_map/tests/test_categorizer.py` (caso adicional)

### Implementation for User Story 3

- [X] T024 [US3] Garantir categoria/pasta obrigatória: rotear indeterminada → `_A_Revisar` e registrar E-07 (RN-3) na integração de classificação (depende T021, T022)
- [X] T025 [US3] Registrar exceções fail-soft ao longo do pipeline (E-02 PDF ilegível, E-04 página com erro, E-05 sem âncoras, E-06 sem título, E-12 "revisar cruzamento") via `reports.py` (depende T009, T015, T017)
- [X] T026 [US3] Emitir `fase_a_relatorio.csv` consolidado ao fim da execução em `.../superlogica_download_map/reports.py` (depende T009)
- [X] T027 [US3] Validar proveniência antes do append em `mapa.py` (recusar/registrar linha sem `pdf_origem`/`hyperlink_origem`/`pasta_destino`) (depende T016)

**Checkpoint**: nada é perdido/misturado em silêncio; relatório auditável produzido.

---

## Phase 6: User Story 4 - Execução resiliente e retomável (Priority: P2)

**Goal**: fail-soft continua, escrita incremental sobrevive à interrupção, re-execução idempotente, backoff em rate-limit.

**Independent Test**: interromper no meio preserva o progresso no mapa; re-executar não duplica; PDF ilegível e link com erro não interrompem; rate-limit dispara retry/backoff.

### Tests for User Story 4 ⚠️

- [X] T028 [P] [US4] Unit tests de idempotência/dedup por `url_download` + append incremental em `.../superlogica_download_map/tests/test_mapa_idempotencia.py`
- [X] T029 [P] [US4] Unit test de retry/backoff com HTTP mockado (esgota tentativas → trata como E-04) em `.../superlogica_download_map/tests/test_superlogica_parse.py` (caso adicional)

### Implementation for User Story 4

- [X] T030 [US4] Implementar idempotência em `mapa.py` — carregar conjunto de `url_download` existentes na inicialização e pular duplicatas no append (RN-6) (depende T016)
- [X] T031 [US4] Implementar retry com backoff + pausa entre requisições em `superlogica.py` (E-10); esgotado → E-04 (depende T014, usa config de T005)
- [X] T032 [US4] Garantir flush por linha (progresso em disco) e caminhos fail-soft: E-02 pula para o próximo PDF; E-01 permanece fatal (depende T016, T017)

**Checkpoint**: execução robusta a falhas e retomável sem duplicação.

---

## Phase 7: User Story 5 - Passada de reconhecimento de categorias (Priority: P2)

**Goal**: `--recon` coleta categorias distintas + pasta proposta → `categorias_encontradas.csv`, e para para revisão humana.

**Independent Test**: `--recon` emite o inventário com cada categoria distinta e sua pasta proposta; após ajuste do dicionário, o mapa reflete a mudança.

### Tests for User Story 5 ⚠️

- [X] T033 [P] [US5] Unit test da agregação de reconhecimento (categorias distintas + chave canônica + pasta proposta) com extração mockada em `.../superlogica_download_map/tests/test_categorizer.py` (caso adicional)

### Implementation for User Story 5

- [X] T034 [US5] Implementar a passada de reconhecimento em `reports.py` — varrer PDFs, coletar `categoria_bruta` distintas + chave canônica + `pasta_destino_proposta`, emitir `categorias_encontradas.csv` (depende T013, T015, T020, T021)
- [X] T035 [US5] Ligar a flag `--recon` na `cli.py` para executar o reconhecimento e **parar** (não gerar o mapa) (depende T010, T034)

**Checkpoint**: classificação auditável antes de comprometer o mapa.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: acabamento que afeta múltiplas stories

- [X] T036 [P] Resumo final na `cli.py` — nº de PDFs lidos, hyperlinks resolvidos, arquivos mapeados, exceções por tipo (Passo 9)
- [X] T037 [P] Documentação: `README.md` do pacote apontando para `quickstart.md` em `.../superlogica_download_map/README.md`
- [X] T038 Rodar ruff + `pytest` completo; garantir ≥80% de cobertura na lógica de negócio (`uv run pytest .../superlogica_download_map/tests`)
- [X] T039 Validar `quickstart.md` (fluxo `--recon` e execução completa com mocks); confirmar que nenhum arquivo-alvo é baixado (FR-025)
- [X] T040 [P] Verificar segurança: `git status` não mostra `credentials.json`/`token.json` staged; regras de `.gitignore` efetivas (SC-011)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — **BLOQUEIA** todas as user stories.
- **US1 (Phase 3)**: depende da Foundational. É o MVP de navegação.
- **US2 (Phase 4)**: depende da Foundational; integra-se ao pipeline da US1 (T022 depende de T015/T016).
- **US3 (Phase 5)**: depende de US1 + US2 (roteamento `_A_Revisar` usa o categorizador).
- **US4 (Phase 6)**: depende de US1 (mapa/superlógica); independente de US2/US3 na lógica pura.
- **US5 (Phase 7)**: depende de US1 (leitura/extração) + US2 (categorizador).
- **Polish (Phase 8)**: depende das stories desejadas concluídas.

### User Story Dependencies

- **US1 (P1)**: após Foundational. Base do pipeline.
- **US2 (P1)**: após Foundational; consome pontos de extensão da US1 para preencher a classificação.
- **US3 (P1)**: após US1+US2 (rede de segurança sobre a classificação e o pipeline).
- **US4 (P2)**: após US1 (resiliência sobre a I/O já existente).
- **US5 (P2)**: após US1+US2 (reusa extração e categorizador).

### Within Each User Story

- Testes escritos antes e devem FALHAR antes da implementação.
- Funções puras (split/categorizador/sanitização) antes da integração no pipeline.
- Writers/serviços antes da ligação na CLI.

---

## Parallel Opportunities

- **Setup**: T003 e T004 em paralelo.
- **Foundational**: T006/T007 (sanitize) em paralelo com T008 (auth); T005 (config) é pré-requisito comum.
- **US1**: T011/T012 (testes) em paralelo; T013 e T014 em paralelo (arquivos distintos: `drive_reader.py` vs `superlogica.py`); T015 depende de config.
- **US2**: T018/T019 (testes) em paralelo; T020 (split) em paralelo com o início de T021.
- **US4**: T028/T029 (testes) em paralelo; T030 (`mapa.py`) em paralelo com T031 (`superlogica.py`).

### Parallel Example: User Story 1

```bash
# Testes da US1 juntos:
Task: "Parse de âncoras a partir de HTML fixture em tests/test_superlogica_parse.py"
Task: "Cruzamento link↔célula em PDF sintético em tests/test_pdf_extractor.py"

# Implementações independentes da US1 (arquivos distintos):
Task: "drive_reader.py — listar/baixar PDFs recursivo"
Task: "superlogica.py — GET + parse de todas as âncoras"
```

---

## Implementation Strategy

### MVP First (P1: US1 → US2 → US3)

1. Phase 1 (Setup) + Phase 2 (Foundational).
2. **US1**: pipeline de ponta a ponta produz o mapa (navegação).
3. **US2**: classificação por categoria preenche `pasta_destino` (satisfaz "categoria obrigatória").
4. **US3**: rede de segurança + relatório de exceções.
5. **PARAR e VALIDAR**: mapa completo, classificado e auditável — entregável funcional para a Fase B.

### Incremental Delivery

- MVP (US1+US2+US3) → +US4 (resiliência/retomada) → +US5 (reconhecimento).
- Cada incremento agrega valor sem quebrar os anteriores.

---

## Notes

- `[P]` = arquivos diferentes, sem dependências pendentes.
- Credenciais e saídas **nunca** versionadas; o código vive em pacote rastreável, o cwd guarda `credentials.json`/`token.json`/saídas (ignorados).
- Cada story deve ser validável isoladamente; commit por tarefa ou grupo lógico (Conventional Commits).
- Evitar: tarefas vagas, conflito no mesmo arquivo, dependências entre stories que quebrem a independência de teste.

**Total de tarefas**: 40 (T001–T040).
