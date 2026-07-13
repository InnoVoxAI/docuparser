# Implementation Plan: Fase A — Extração e geração do mapa de download

**Branch**: `012-download-map-extraction` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `docs/specs/012-download-map-extraction/spec.md`

**Fonte-roteiro**: [docuparse-project/scripts/SELECT/downloads/fases/fase_a_extracao.md](../../../docuparse-project/scripts/SELECT/downloads/fases/fase_a_extracao.md) (roteiro técnico detalhado do humano; base da spec e deste plano)

## Summary

Construir uma **utilidade de linha de comando (CLI)** em Python que gera o *mapa de download* da Fase A: autentica no Google Drive (OAuth read-only), lê os PDFs-lista de duas pastas designadas, extrai de cada linha da tabela o hyperlink + a categoria (cruzando as camadas de anotações de link e texto por coordenadas — Salto 1), resolve cada hyperlink na página pública do Superlógica e raspa **todas** as âncoras de download (Salto 2), classifica cada arquivo numa pasta de destino derivada da categoria e grava um `mapa_download.csv` **incremental e idempotente** — sem baixar nenhum arquivo-alvo (isso é a Fase B). Bibliotecas centrais já presentes no projeto: **PyMuPDF** (links+texto com geometria), **BeautifulSoup+lxml** (HTML), **requests** (HTTP), **Typer** (CLI); dependência nova: **cliente OAuth/Drive do Google**. O código fica num pacote **rastreável** sob `scripts/SELECT/`, enquanto credenciais e saídas ficam no **diretório de trabalho** (cwd, tipicamente `.../downloads/fases/`, já ignorado pelo git).

## Technical Context

**Language/Version**: Python 3.13 (repo `requires-python >=3.13`, `.python-version = 3.13`), gerenciado com **uv** (`pyproject.toml` + `uv.lock`).

**Primary Dependencies**:
- **PyMuPDF** (`pymupdf`, importado como `pymupdf`/`fitz`) — Salto 1: `page.get_links()` expõe URI + `rect` de cada anotação de link; `page.get_text("words")` expõe palavras com bounding box. Já em `pyproject`.
- **BeautifulSoup4 + lxml** — Salto 2: parse do HTML estático das âncoras de download. Presentes no `uv.lock` (transitivos); **promover a dependências diretas** no `pyproject`.
- **requests** — GET das páginas do Superlógica (retry/backoff manual). Já em `pyproject`.
- **Typer** — entrypoint CLI e flags. Já em `pyproject`.
- **NOVA**: cliente Google — `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2` (fluxo OAuth "Desktop app" read-only + Drive API v3 para listar/baixar PDFs). Adicionar via `uv add`.

**Storage**: sistema de arquivos local, relativo ao diretório de execução (cwd). Saídas: `mapa_download.csv` (entregável), `fase_a_relatorio.csv` (exceções), `categorias_encontradas.csv` (reconhecimento), e a árvore `downloads/<pasta_destino>/` (só estrutura, sem arquivos-alvo). Estado OAuth: `token.json` (gerado no 1º login). Nenhum banco de dados.

**Testing**: **pytest**. Unit tests **sem rede/disco** (exigência da constituição) para a lógica pura: divisão categoria↔complemento, normalização + regras de família + fallback, sanitização de nomes, idempotência/dedup do mapa. I/O externo (Drive, Superlógica) mockado; extração de PDF testada contra 1–2 PDFs sintéticos em `fixtures/`.

**Target Platform**: Linux, execução local/desktop (o fluxo OAuth abre o navegador no 1º login). Não é um serviço containerizado; é uma ferramenta operada manualmente.

**Project Type**: CLI / utilitário standalone (single project). Não integra os microserviços do produto nem seus endpoints.

**Performance Goals**: processar o universo das duas pastas do Drive (recursivo) em **uma única execução não supervisionada** (após o login inicial). Um PDF por vez em memória; **escrita incremental** do mapa (nunca montar tudo em memória). Educação de rede com o Superlógica: pausa curta entre requisições + retry com backoff (default 3 tentativas). Sem alvo de latência p95 (não é serviço).

**Constraints**: escopo **somente leitura** no Drive; credenciais/token apenas locais e fora do git; **fail-soft** em todas as exceções não-fatais, com única falha fatal = autenticação (E-01); categorização **determinística** e re-execução **idempotente** (dedup por `url_download`); **nenhum** arquivo-alvo baixado; toda saída local relativa ao cwd.

**Scale/Scope**: 2 pastas do Drive (recursivo) → N PDFs-lista → M linhas com hyperlink → K âncoras de download (K ≥ M; um hyperlink → N arquivos). Ordem de grandeza: dezenas a centenas de arquivos, de um único condomínio. Execução single-machine, single-run.

**Links das pastas do Drive** (fornecidos pelo humano; IDs já refletidos na spec/config):
1. `https://drive.google.com/drive/folders/1uJ6cZYbThBxiKcfcMmrlS-9dn-aVJfzr`
2. `https://drive.google.com/drive/folders/13r1wG8rj8YFvYefPoDYhFg-aVESRZMgE`

## Constitution Check

*GATE: Deve passar antes da Phase 0. Re-checado após a Phase 1.*

| Princípio | Avaliação para esta feature | Situação |
|---|---|---|
| **I. Code Quality** | Type hints em todo o código; funções single-purpose ≤50 linhas e arquivos ≤400 linhas → **modularização obrigatória** (pacote com módulos por salto/responsabilidade), o que também atende o pedido do roteiro de "unidades testáveis isoladamente". Ruff sem violações. **Segurança**: sanitização de nomes de arquivo/pasta contra path traversal e caracteres inválidos (FR-017); URL-decode antes de usar como texto; credenciais **nunca** no código nem no git (FR-004). | ✅ PASS |
| **II. Testing Standards** | Unit tests **sem rede/disco** para lógica pura (split categoria/complemento, normalização/família/fallback, sanitização, dedup/idempotência). Drive/Superlógica **mockados**; extração de PDF validada contra PDFs sintéticos em `fixtures/`. Cobertura ≥80% na lógica de negócio (a fina camada de I/O externo fica coberta por testes com mock). | ✅ PASS |
| **III. UX Consistency** | Envelope de API/WCAG/responsividade/React → **N/A** (não há API nem frontend). Espírito aplicável: **mensagens de erro humanas e acionáveis** (E-01 instrui re-login; relatório de exceções legível), sem stack trace cru ao operador; **terminologia consistente** (categoria, complemento, pasta de destino, mapa). | ✅ PASS (itens web N/A, justificado) |
| **IV. Performance Requirements** | Alvos de latência de API / throughput de OCR / limites de container → **N/A** (não é serviço). Aplicável: **escrita incremental** (memória constante no mapa), um PDF por vez, backoff cortês com o Superlógica; sem timeouts de IA (não há IA). | ✅ PASS (itens de serviço N/A, justificado) |
| **Technology Standards** | O stack travado descreve o **produto** (Django/FastAPI/React/engines OCR/DeepSeek-Ollama). Esta é uma **ferramenta utilitária em `scripts/`**, não runtime do produto. As deps novas (cliente Google Drive) **não** são engine de OCR nem integração de IA na nuvem — os dois pontos que a constituição restringe — logo **não exigem emenda**. Precedente: a 011 adicionou `boto3` marcando PASS. | ✅ PASS (sem emenda; ver research.md) |
| **Development Workflow** | Spec-first cumprido (012). Branch `012-download-map-extraction`. PR referenciará esta spec/plano com plano de testes. Commits Conventional Commits. | ✅ PASS |

**Resultado**: sem violações. Nenhuma entrada em Complexity Tracking necessária.

## Project Structure

### Documentation (this feature)

```text
docs/specs/012-download-map-extraction/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Phase 0 — decisões técnicas + resolução das decisões em aberto
├── data-model.md        # Phase 1 — entidades (entrada do mapa, categoria, exceção, config)
├── quickstart.md        # Phase 1 — setup de credenciais, deps, execução e re-execução
├── contracts/           # Phase 1 — contratos (interface entre A↔B e CLI)
│   ├── mapa-download.md  # Schema do mapa (a interface consumida pela Fase B) — CRÍTICO
│   └── cli-and-config.md # Contrato da CLI, configuração e formatos de relatório/inventário
├── checklists/
│   └── requirements.md  # (criado no /speckit-specify)
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
docuparse-project/scripts/SELECT/
└── superlogica_download_map/            # NOVO pacote RASTREÁVEL (código da Fase A)
    ├── __init__.py
    ├── __main__.py                      # `python -m superlogica_download_map` → chama cli
    ├── cli.py                           # Typer: flags (--work-dir, --recon, --recursive, etc.)
    ├── config.py                        # IDs/URLs das pastas, caminhos default, dicionário de famílias, tolerâncias, retry
    ├── drive_auth.py                    # OAuth desktop read-only + reuso/refresh de token.json (E-01)
    ├── drive_reader.py                  # listar (recursivo, E-11) + obter bytes dos PDFs-lista — Salto 0
    ├── pdf_extractor.py                 # Salto 1: get_links()+words, cruzamento por y, split cat/complemento (5.2/5.2.1)
    ├── superlogica.py                   # Salto 2: GET página (retry/backoff, E-10) + parse âncoras (href + img title)
    ├── categorizer.py                  # normalização (A) + regras de família (B) + fallback (C) → pasta_destino (Seção 6)
    ├── sanitize.py                      # sanitização de nomes de arquivo/pasta (5.3, E-08/E-09)
    ├── mapa.py                          # escrita incremental + idempotência (dedup por url_download, RN-6)
    ├── reports.py                       # relatório de exceções + inventário de categorias (reconhecimento)
    └── tests/
        ├── test_split_categoria.py      # divisão categoria/complemento + casos de borda (RN-8)
        ├── test_categorizer.py          # normalização/família/fallback determinístico
        ├── test_sanitize.py             # sanitização/URL-decode
        ├── test_mapa_idempotencia.py    # dedup por url_download / escrita incremental
        ├── test_superlogica_parse.py    # parse de âncoras a partir de HTML fixture
        ├── test_pdf_extractor.py        # cruzamento link↔categoria em PDF sintético
        └── fixtures/                    # PDF sintético + HTML de exemplo do Superlógica

# Diretório de TRABALHO (cwd na execução; default = onde está credentials.json;
# tipicamente docuparse-project/scripts/SELECT/downloads/fases/ — JÁ ignorado pelo git via `downloads/`)
#   credentials.json            # fornecido pelo operador (gitignored)
#   token.json                  # gerado no 1º login (gitignored)
#   mapa_download.csv           # ENTREGÁVEL — escrito incrementalmente
#   fase_a_relatorio.csv        # relatório de exceções
#   categorias_encontradas.csv  # inventário da passada de reconhecimento
#   downloads/<pasta_destino>/  # estrutura de pastas (vazia na Fase A)
```

**Structure Decision**: separar **local do código** (pacote rastreável `scripts/SELECT/superlogica_download_map/`) do **diretório de trabalho** (cwd com credenciais e saídas). Motivo: o diretório `downloads/` inteiro é ignorado pelo git (confirmado via `git check-ignore`), então código colocado em `.../downloads/fases/` **não seria versionado, testado nem revisado** — violando o fluxo da constituição. O pacote fica versionado e testável; a CLI usa o cwd (ou `--work-dir`) como raiz de credenciais e saídas, honrando o requisito do roteiro de "saída local, relativa ao diretório de execução" (FR-018). O operador executa a partir de `.../downloads/fases/` (onde `credentials.json` já está), e as saídas caem ali (ignoradas). Alternativa (código dentro de `downloads/fases/` com negações no `.gitignore`) foi rejeitada por ser frágil — o git não recurse em diretórios ignorados, exigindo re-inclusão de cada diretório-pai. Ver research.md.

## Complexity Tracking

> Sem violações de constituição. Seção não aplicável.
