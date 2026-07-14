# Implementation Plan: Fase B — Download e organização dos arquivos

**Branch**: `013-file-download-organization` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `docs/specs/013-file-download-organization/spec.md`

**Fonte-roteiro**: [docuparse-project/scripts/SELECT/downloads/fases/fase_b_download.md](../../../docuparse-project/scripts/SELECT/downloads/fases/fase_b_download.md) (roteiro técnico detalhado do humano; base da spec e deste plano)

**Depende de**: [spec 012 — Fase A](../012-download-map-extraction/spec.md). A interface é o contrato [`mapa_download.csv`](../012-download-map-extraction/contracts/mapa-download.md). A Fase B **consome** esse mapa; deve ser desenvolvida **depois** da Fase A.

## Summary

Construir uma segunda **utilidade de linha de comando (CLI)** em Python que executa a Fase B: lê o `mapa_download.csv` produzido pela Fase A (uma linha por arquivo, já classificada), e para cada linha pendente faz o **Salto 3** — um **GET público simples** na `url_download` do Superlógica (sem login/OAuth) que retorna os bytes do arquivo. Cada conteúdo é **validado** (assinatura `%PDF`/content-type — E-05), gravado de forma **atômica** (`.part` → rename — E-11) em `downloads/<pasta_destino>/<nome_final>` (com anti-colisão **determinística** — E-06), e imediatamente registrado no **CSV final** (`relatorio_final.csv`, o entregável central). O `status` de cada linha do mapa é atualizado (`baixado`/`erro`), tornando a execução **interrompível e retomável** sem rebaixar nem duplicar (RN-4/E-12). Falhas são **fail-soft**: vão para `fase_b_erros.csv` com motivo e nº de tentativas; casos de **provável expiração** de `accesskey`/`hash` são sinalizados (E-04). Bibliotecas centrais já presentes no projeto: **requests** (HTTP com retry/backoff/pausa) e **Typer** (CLI); **nenhuma dependência nova** (a Fase B não usa Google Drive, PyMuPDF nem BeautifulSoup). O código fica num pacote **rastreável** irmão da Fase A sob `scripts/SELECT/`, **reaproveitando** a utilidade de sanitização já validada; credenciais não são usadas, e mapa/downloads/saídas ficam no **diretório de trabalho** (cwd, tipicamente `.../downloads/fases/`, já ignorado pelo git).

## Technical Context

**Language/Version**: Python 3.13 (repo `requires-python >=3.13`, `.python-version = 3.13`), gerenciado com **uv** (`pyproject.toml` + `uv.lock`).

**Primary Dependencies**:
- **requests** — Salto 3: GET público na `url_download` com sessão reutilizada, `timeout`, retry/backoff manual e pausa entre requisições (E-03/E-09/E-10). Já em `pyproject`.
- **Typer** — entrypoint CLI e flags. Já em `pyproject`.
- **Reuso interno** (não é dependência nova): `superlogica_download_map.sanitize` (sanitização de nomes de arquivo/pasta — E-07), importado do pacote irmão da Fase A. Ambos os pacotes são importáveis a partir do diretório `scripts/SELECT/` (o `conftest.py` já adiciona esse diretório ao `sys.path`).
- **NENHUMA dependência nova**: a Fase B **não** usa `google-*`, **não** usa `pymupdf`, **não** usa `beautifulsoup4/lxml`. Validação de conteúdo é por **assinatura de bytes** (`%PDF`) + `Content-Type`, sem parser de HTML.

**Storage**: sistema de arquivos local, relativo ao diretório de execução (cwd). Entrada: `mapa_download.csv` (ou `.json`) da Fase A. Saídas: `relatorio_final.csv` (**entregável**, escrito incrementalmente), `fase_b_erros.csv` (relatório de erros), o mapa com a coluna `status` atualizada, e a árvore `downloads/<pasta_destino>/<arquivo>` (agora **com** os arquivos). Nenhum banco de dados. **Sem `credentials.json`/`token.json`** (não há OAuth na Fase B).

**Testing**: **pytest**. Unit tests **sem rede/disco** (exigência da constituição) para a lógica pura: validação de conteúdo (`%PDF` vs HTML), nomeação anti-colisão determinística, resolução de retomada (status + presença em disco), dedup do CSV final, detecção do padrão de expiração (E-04), leitura/validação de colunas do mapa. O I/O de rede (`requests`) é **injetado/mockado** (sessão fake devolvendo respostas sintéticas); a escrita atômica é testada com `tmp_path` (I/O de disco isolado do pytest é aceitável em teste de integração leve, mas a lógica de decisão fica em funções puras testadas sem disco).

**Target Platform**: Linux, execução local/desktop. Não é um serviço containerizado; é uma ferramenta operada manualmente, tipicamente logo após a Fase A.

**Project Type**: CLI / utilitário standalone (single project), **irmão** da CLI da Fase A. Não integra os microserviços do produto nem seus endpoints.

**Performance Goals**: processar **todo** o `mapa_download.csv` em uma única execução não supervisionada, **retomável** se interrompida. Um arquivo por vez em memória/streaming para disco; **escrita incremental** do CSV final e do status (nunca acumular tudo em memória). Educação de rede com o Superlógica: pausa curta configurável entre requisições + retry com backoff (default 3 tentativas). Sem alvo de latência p95 (não é serviço).

**Constraints**: **zero acesso ao Google Drive e zero uso de OAuth** (FR-003/SC-007); escrita **somente local** relativa ao cwd (FR-015); **fail-soft** em toda exceção não-fatal (fatais = mapa ausente/ilegível e falha de escrita generalizada); gravação **atômica** (nunca arquivo truncado com nome final — SC-002); anti-colisão **determinística** e sem sobrescrita (SC-004); re-execução **idempotente** (dedup por `url_download`, retomada por `status` + presença em disco — SC-005/SC-006); a Fase B **não** re-executa a heurística de categoria (as pastas vêm prontas do mapa).

**Scale/Scope**: N linhas do mapa (ordem de dezenas a centenas de arquivos de um único condomínio) → N GETs públicos → N arquivos salvos → N linhas no CSV final. Execução single-machine, single-run, retomável.

## Constitution Check

*GATE: Deve passar antes da Phase 0. Re-checado após a Phase 1.*

| Princípio | Avaliação para esta feature | Situação |
|---|---|---|
| **I. Code Quality** | Type hints em todo o código; funções single-purpose ≤50 linhas e arquivos ≤400 linhas → **modularização** (pacote com módulos por responsabilidade: leitura do mapa, download, validação, nomeação/atômico, saídas, orquestração). Ruff sem violações. **Segurança**: sanitização de `nome_arquivo`/`pasta_destino` contra path traversal e caracteres inválidos **reusando** o `sanitize` já validado (E-07); GET **somente** na `url_download` do mapa; nenhum segredo no código nem no git (não há credenciais na Fase B). | ✅ PASS |
| **II. Testing Standards** | Unit tests **sem rede/disco** para a lógica pura (validação `%PDF`/content-type, anti-colisão determinística, decisão de retomada, dedup do CSV final, sinal de expiração E-04, validação de colunas do mapa). `requests` **injetado/mockado** (sessão fake). Escrita atômica coberta por teste com `tmp_path`. Cobertura ≥80% na lógica de negócio. | ✅ PASS |
| **III. UX Consistency** | Envelope de API/WCAG/responsividade/React → **N/A** (não há API nem frontend). Espírito aplicável: **mensagens de erro humanas e acionáveis** (E-01 instrui rodar a Fase A; E-04 recomenda renovar as URLs re-rodando a Fase A; resumo final legível), sem stack trace cru ao operador; **terminologia consistente** com a Fase A (mapa, `pasta_destino`, categoria, `url_download`, status). | ✅ PASS (itens web N/A, justificado) |
| **IV. Performance Requirements** | Alvos de latência de API / throughput de OCR / limites de container → **N/A** (não é serviço). Aplicável: **escrita incremental** (memória constante), streaming do download para o `.part`, pausa/backoff cortês com o Superlógica; sem timeouts de IA (não há IA). | ✅ PASS (itens de serviço N/A, justificado) |
| **Technology Standards** | O stack travado descreve o **produto** (Django/FastAPI/React/engines OCR/DeepSeek-Ollama). Esta é uma **ferramenta utilitária em `scripts/`**, não runtime do produto, e **não adiciona nenhuma dependência** (usa `requests`/`Typer` já presentes). Não há engine de OCR nem integração de IA na nuvem — os dois pontos que a constituição restringe. **Não exige emenda**. Precedente: 011 (`boto3`) e 012 (cliente Google) marcaram PASS. | ✅ PASS (sem emenda; ver research.md) |
| **Development Workflow** | Spec-first cumprido (013). Branch `013-file-download-organization`. PR referenciará esta spec/plano com plano de testes. Commits Conventional Commits. | ✅ PASS |

**Resultado**: sem violações. Nenhuma entrada em Complexity Tracking necessária.

## Project Structure

### Documentation (this feature)

```text
docs/specs/013-file-download-organization/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Phase 0 — decisões técnicas + resolução das decisões em aberto do roteiro
├── data-model.md        # Phase 1 — entidades (linha do mapa, resultado de download, linha do CSV final, erro, status, config)
├── quickstart.md        # Phase 1 — pré-requisitos (mapa da Fase A), execução, retomada, expiração
├── contracts/           # Phase 1 — contratos que a Fase B expõe
│   ├── relatorio-final.md    # Schema do CSV final (entregável central) — CRÍTICO
│   ├── fase-b-erros.md       # Schema do relatório de erros (com sinal de expiração E-04)
│   └── cli-and-config.md     # Contrato da CLI, configuração e códigos de saída
├── checklists/
│   └── requirements.md  # (criado no /speckit-specify)
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
docuparse-project/scripts/SELECT/
├── superlogica_download_map/            # Pacote da Fase A (spec 012) — JÁ EXISTE
│   └── sanitize.py                      # REUSADO pela Fase B (import direto)
└── superlogica_file_downloader/         # NOVO pacote RASTREÁVEL (código da Fase B)
    ├── __init__.py
    ├── __main__.py                      # `python -m superlogica_file_downloader` → chama cli
    ├── cli.py                           # Typer: flags (--work-dir, --map, --downloads-root, --final-csv, --errors, --pause, --timeout, --retries, --map-format)
    ├── config.py                        # caminhos default, política de HTTP (pausa/timeout/retry), assinatura PDF, colunas do CSV final
    ├── map_io.py                        # Passo 1/2: ler o mapa (csv/json) + validar colunas (E-01) + atualizar coluna status (RN-4, retomada)
    ├── downloader.py                    # Salto 3: GET público com sessão, timeout, retry/backoff, pausa (E-03/E-09/E-10) + detecção de expiração (E-04)
    ├── content.py                       # validação do conteúdo baixado: assinatura %PDF + Content-Type (E-05)
    ├── naming.py                        # nome final: sanitize (reuso) + garantia de extensão + anti-colisão determinística (E-06/E-07)
    ├── atomic.py                        # gravação atômica: escrever em <destino>.part → renomear após validação (E-11)
    ├── outputs.py                       # CSV final incremental + dedup por url_download (RN-5/RN-6) e relatório de erros (E-04 sinalizado)
    ├── pipeline.py                      # orquestração (Passo 3): iterar pendentes, fail-soft, resumo final (E-12)
    └── tests/
        ├── conftest.py                  # adiciona scripts/SELECT ao sys.path (import dos dois pacotes)
        ├── test_content.py              # %PDF vs HTML de erro/login (E-05) + sinal de expiração (E-04)
        ├── test_naming.py               # anti-colisão determinística + garantia de extensão + sanitização (E-06/E-07)
        ├── test_resume.py              # decisão de retomada (status + presença em disco) e dedup do CSV final (RN-4/RN-6/E-12)
        ├── test_map_io.py               # leitura + validação de colunas do mapa; ausência → fatal (E-01/E-02)
        ├── test_downloader.py           # retry/backoff/pausa com sessão mockada; esgotamento → erro (E-03/E-10)
        └── test_atomic.py               # .part → rename; interrupção não deixa nome final truncado (E-11, usa tmp_path)

# Diretório de TRABALHO (cwd na execução; tipicamente
# docuparse-project/scripts/SELECT/downloads/fases/ — JÁ ignorado pelo git via `downloads/`)
#   mapa_download.csv           # ENTRADA — produzida pela Fase A (contrato 012)
#   relatorio_final.csv         # ENTREGÁVEL — escrito incrementalmente pela Fase B
#   fase_b_erros.csv            # relatório de erros (com sinal de expiração E-04)
#   downloads/<pasta_destino>/  # árvore de pastas AGORA com os arquivos baixados
#   (SEM credentials.json / token.json — não há OAuth na Fase B)
```

**Structure Decision**: criar um **pacote irmão rastreável** `scripts/SELECT/superlogica_file_downloader/`, separado do pacote da Fase A, porque as duas fases são **ferramentas independentes** com CLIs, entrypoints e ciclos de execução distintos (a Fase B roda sozinha a partir do mapa, sem Drive). O acoplamento entre elas é intencionalmente mínimo: a **interface** é o arquivo `mapa_download.csv` (contrato 012), não código compartilhado — a única exceção é **reusar a sanitização já validada** (`superlogica_download_map.sanitize`) via import, evitando duplicar essa lógica de segurança (DRY, "No Dead Code"). Ambos os pacotes vivem sob `scripts/SELECT/` e são importáveis como irmãos (o `conftest.py` adiciona esse diretório ao `sys.path`, como já feito na Fase A). Como na 012, separa-se **local do código** (pacote versionado/testável) do **diretório de trabalho** (cwd com mapa, downloads e saídas — tudo sob `downloads/`, ignorado pelo git), honrando o requisito de "saída local, relativa ao diretório de execução" (FR-015). Alternativa (juntar a Fase B como subcomando do pacote da Fase A) foi rejeitada: misturaria a dependência pesada de Drive/PyMuPDF/bs4 (Fase A) numa ferramenta que precisa **só** de `requests` (Fase B), e borraria a fronteira das duas fases que a arquitetura existe para isolar. Ver research.md.

## Complexity Tracking

> Sem violações de constituição. Seção não aplicável.
