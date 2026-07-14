# superlogica_download_map — Fase A (mapa de download)

Utilitário de linha de comando que **descobre e cataloga** os arquivos de despesas
a serem baixados na Fase B, a partir de PDFs-lista no Google Drive. **Não baixa**
os arquivos-alvo (isso é a Fase B).

Spec, plano e contratos: [`docs/specs/012-download-map-extraction/`](../../../../docs/specs/012-download-map-extraction/).

## O que faz (3 saltos)

1. **Drive** (OAuth read-only): lê os PDFs-lista de duas pastas designadas.
2. **PDF**: cruza anotações de link ↔ texto por coordenadas para achar, em cada
   linha, o hyperlink (coluna Fornecedor) e a categoria (coluna Categoria - Complemento).
3. **Superlógica**: resolve cada hyperlink na página pública e raspa **todas** as
   âncoras de download.

Grava, incrementalmente e de forma idempotente, `mapa_download.csv` (uma linha por
arquivo), classificado em pastas por categoria, mais um relatório de exceções.

## Uso

A partir do diretório do pacote (`scripts/SELECT`):

```bash
# 1) (recomendado) passada de reconhecimento — revise categorias/pastas antes do mapa
uv run python -m superlogica_download_map --work-dir downloads/fases --recon

# 2) gerar o mapa
uv run python -m superlogica_download_map --work-dir downloads/fases
```

`--work-dir` é onde estão `credentials.json` (fornecido) e `token.json` (gerado no
1º login), e onde as saídas são escritas.

| Flag | Padrão | Efeito |
|---|---|---|
| `--work-dir PATH` | `.` | Raiz de credenciais e saídas |
| `--recon` | off | Só o inventário de categorias, e para |
| `--recursive/--no-recursive` | recursive | Varrer subpastas do Drive |
| `--map-format csv\|json` | csv | Formato do mapa (json = JSON Lines) |
| `--credentials PATH` | `<work-dir>/credentials.json` | Credencial OAuth |
| `--verbose` | off | Log em nível debug |

Exit codes: `0` sucesso · `2` falha fatal de autenticação (apague `token.json` e
refaça o login) · `1` erro inesperado.

## Saídas (no `--work-dir`, ignorado pelo git)

- `mapa_download.csv` — entregável consumido pela Fase B (ver `contracts/mapa-download.md`)
- `fase_a_relatorio.csv` — exceções para revisão humana
- `categorias_encontradas.csv` — inventário do `--recon`
- `downloads/<pasta_destino>/` — estrutura de pastas (vazia nesta fase)

## Configuração

Constantes em [`config.py`](config.py): IDs das pastas do Drive, `FAMILY_RULES`
(dicionário de categorias → pasta), tolerância de cruzamento e política de HTTP.

## Testes

```bash
uv run pytest docuparse-project/scripts/SELECT/superlogica_download_map/tests -q
```

Unit tests de lógica pura não tocam rede/disco; Drive e Superlógica são mockados e
a extração de PDF usa fixtures.
