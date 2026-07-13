# Phase 1 — Data Model: Fase A (mapa de download)

Entidades **lógicas** manipuladas pela Fase A. Não há banco de dados; a persistência é em arquivos locais (CSV). Tipos indicam a semântica, não o esquema de um DB.

## Entidade central: `EntradaDoMapa` (linha de `mapa_download.csv`)

Representa **um arquivo a ser baixado na Fase B**. É a unidade de saída e a interface com a Fase B (ver `contracts/mapa-download.md`).

| Campo | Tipo | Origem | Regras / validação |
|---|---|---|---|
| `url_download` | string (URL absoluta) | Salto 2 (`href` da âncora) | Obrigatório. **Chave de idempotência/dedup** (RN-6). Endpoint `.../publico/downloadarquivo?id=...&hash=...`. |
| `nome_arquivo` | string | Salto 2 (`title` do `<img>`) | Obrigatório. Nome real; se ausente → fallback determinístico `{fornecedor_sanitizado}_{id_da_url}.pdf` (E-06). Sanitizado (5.3). |
| `fornecedor` | string | Salto 1 (coluna Fornecedor) | Obrigatório. URL-decode quando vindo de parâmetro. |
| `categoria_bruta` | string | Salto 1 (antes do 1º ` - `) | Obrigatório. Só a categoria, sem complemento (RN-8). |
| `complemento` | string | Salto 1 (depois do 1º ` - `) | Pode ser vazio. |
| `pasta_destino` | string | Heurística (Seção 6) | Obrigatório. Nome de pasta derivado da categoria; nunca vazio (fallback `_A_Revisar`, RN-3/E-07). Sanitizado. |
| `hyperlink_origem` | string (URL) | Salto 1 (`href` da anotação) | Obrigatório. Página `publico/arquivos?...` de origem. |
| `pdf_origem` | string | Salto 0 | Obrigatório. Nome do PDF-lista de onde a linha veio (rastreabilidade, RN-4). |
| `status` | enum | fixo | Valor inicial `pendente`. A Fase B atualiza para `baixado`/`erro`. |

**Invariantes**:
- Toda entrada tem `categoria_bruta` e `pasta_destino` não-vazios (RN-3).
- `url_download` é única no mapa (RN-6).
- Todos os arquivos de um mesmo `hyperlink_origem` compartilham `categoria_bruta`/`complemento` (RN-2).
- Uma página com N âncoras gera N entradas (RN-1).

**Transições de `status`** (a Fase A só cria `pendente`; demais transições são da Fase B):
```
(nova entrada) → pendente → [Fase B] → baixado
                                     ↘ erro
```

## `CategoriaCanonica` (classificação)

Deriva `pasta_destino` a partir de `categoria_bruta` (Seção 6). Não é persistida como linha própria (exceto no inventário de reconhecimento).

| Campo | Tipo | Regras |
|---|---|---|
| `categoria_bruta` | string | Entrada (isolada do complemento). |
| `chave_canonica` | string | minúsculas + sem acento (Unicode→ASCII) + sem pontuação + espaços colapsados. |
| `pasta_destino` | string | (A) igualdade por chave canônica → (B) regra de família casada → (C) Title Case próprio → `_A_Revisar`. |

Regras (`config.py`, ordenadas; primeira que casa vence) — ponto de partida a validar pela passada de reconhecimento:
```
^(constru|reforma|obra)  -> Construção-Reformas
^manut                   -> Manutenções
^(agua|hidr)             -> Água
^(energia|luz|ele)       -> Energia
^(limp|faxina)           -> Limpeza
^(jardi|paisag)          -> Jardinagem
^(segur|portar|vigi)     -> Segurança
^(admin|taxa|hono)       -> Administração
```

## `RegistroDeExcecao` (linha de `fase_a_relatorio.csv`)

Ocorrência não-fatal que exige atenção humana (fail-soft).

| Campo | Tipo | Descrição |
|---|---|---|
| `tipo` | enum | `E-02`,`E-04`,`E-05`,`E-06`,`E-07`,`E-12`, ... |
| `origem` | string | PDF, hyperlink e/ou fornecedor relacionados. |
| `detalhe` | string | Mensagem legível (ex.: "404 na página", "categoria indeterminada", "revisar cruzamento"). |
| `acao_tomada` | string | Ex.: "pulado", "→ _A_Revisar", "fallback de nome". |

## `CategoriaEncontrada` (linha de `categorias_encontradas.csv` — passada de reconhecimento)

| Campo | Tipo | Descrição |
|---|---|---|
| `categoria_bruta` | string | Categoria distinta observada (isolada). |
| `chave_canonica` | string | Chave canônica correspondente. |
| `pasta_destino_proposta` | string | Pasta que a heurística atual atribuiria. |

## `Config` (constantes parametrizáveis — `config.py`, FR-024)

| Campo | Default | Descrição |
|---|---|---|
| `DRIVE_FOLDER_IDS` | `[1uJ6...VJfzr, 13r1...RZMgE]` | IDs das duas pastas do Drive. |
| `DRIVE_SCOPE` | `drive.readonly` | Escopo OAuth. |
| `RECURSIVE` | `true` | Varredura recursiva de subpastas (E-11). |
| `WORK_DIR` | `.` (cwd) | Raiz de credenciais e saídas. |
| `CREDENTIALS_FILE` / `TOKEN_FILE` | `credentials.json` / `token.json` | No work-dir. |
| `MAP_PATH` / `REPORT_PATH` / `CATEGORIES_PATH` | `mapa_download.csv` / `fase_a_relatorio.csv` / `categorias_encontradas.csv` | Saídas. |
| `DOWNLOADS_ROOT` | `downloads` | Raiz da estrutura de pastas de destino. |
| `MAP_FORMAT` | `csv` | `csv` \| `json`. |
| `FAMILY_RULES` | (ver acima) | Dicionário ordenado de famílias. |
| `Y_TOLERANCE_RATIO` | `0.5` | Tolerância de cruzamento vertical (× altura média de linha). |
| `HTTP_RETRIES` / `HTTP_BACKOFF_BASE_S` / `HTTP_PAUSE_S` | `3` / configurável / configurável | Política de retry/pausa (E-10). |

## Entidades de entrada (não persistidas)

- **PDF-lista**: documento no Drive; tabela com cabeçalho `Vencimento | Fornecedor | Categoria - Complemento | Compet. | Valor`; link na coluna Fornecedor.
- **Página de arquivos (Superlógica)**: HTML público (autorizado por `accesskey`) com ≥1 âncora `<a>` de download (`href` + `<img title>`).
- **Credencial OAuth**: `credentials.json` (fornecido) + `token.json` (gerado), no work-dir.
